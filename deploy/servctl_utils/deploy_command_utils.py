import collections
import glob
import logging
import os
from pprint import pformat

import time

from deploy.servctl_utils.other_command_utils import check_kubernetes_context, set_environment, get_disk_names
from deploy.servctl_utils.kubectl_utils import is_pod_running, get_pod_name, get_node_name, run_in_pod, \
    wait_until_pod_is_running as sleep_until_pod_is_running, wait_until_pod_is_ready as sleep_until_pod_is_ready, \
    wait_for_resource, wait_for_not_resource
from deploy.servctl_utils.yaml_settings_utils import process_jinja_template, load_settings
from deploy.servctl_utils.shell_utils import run

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


DEPLOYABLE_COMPONENTS = [
    "init-cluster",
    "settings",
    "secrets",

    "external-elasticsearch-connector",

    "elasticsearch",
    "postgres",
    "redis",
    "seqr",
    "kibana",
    "nginx",
    "pipeline-runner",

    "kube-scan",
]

DEPLOYMENT_TARGETS = {}
DEPLOYMENT_TARGETS["gcloud-prod"] = [
    "init-cluster",
    "settings",
    "secrets",
    "nginx",
    "postgres",
    "external-elasticsearch-connector",
    "kibana",
    "redis",
    "seqr",
    #"pipeline-runner",
    "kube-scan",
]


DEPLOYMENT_TARGETS["gcloud-dev"] = DEPLOYMENT_TARGETS["gcloud-prod"]

DEPLOYMENT_TARGETS['gcloud-prod-elasticsearch'] = [
    'init-cluster',
    'settings',
    'secrets',
    'elasticsearch',
    'kube-scan',
]
DEPLOYMENT_TARGETS['gcloud-dev-es'] = DEPLOYMENT_TARGETS['gcloud-prod-elasticsearch']

GCLOUD_CLIENT = 'gcloud-client'

SECRETS = {
    'elasticsearch': ['users', 'users_roles', 'roles.yml'],
    GCLOUD_CLIENT: ['service-account-key.json'],
    'kibana': ['elasticsearch.password'],
    'matchbox': ['{deploy_to}/config.json'],
    'nginx': ['{deploy_to}/tls.key', '{deploy_to}/tls.crt'],
    'postgres': ['postgres.username', 'postgres.password'],
    'seqr': [
        'omim_key', 'postmark_server_token', 'slack_token', 'airtable_key', 'django_key', 'seqr_es_password',
    ],
}

DEPLOYMENT_TARGET_SECRETS = {
    'gcloud-prod': [
        'seqr',
        'postgres',
        'nginx',
        'matchbox',
        'kibana',
        GCLOUD_CLIENT,
    ],
    'gcloud-prod-elasticsearch': [
        'elasticsearch',
    ],
}
DEPLOYMENT_TARGET_SECRETS['gcloud-dev'] = DEPLOYMENT_TARGET_SECRETS['gcloud-prod']
DEPLOYMENT_TARGET_SECRETS['gcloud-dev-es'] = DEPLOYMENT_TARGET_SECRETS['gcloud-prod-elasticsearch']


def deploy_init_cluster(settings):
    """Provisions a GKE cluster, persistent disks, and any other prerequisites for deployment."""

    print_separator("init-cluster")

    # initialize the VM
    if settings["DEPLOY_TO_PREFIX"] == "gcloud":
        _init_cluster_gcloud(settings)
    else:
        raise ValueError("Unexpected DEPLOY_TO_PREFIX: %(DEPLOY_TO_PREFIX)s" % settings)

    node_name = get_node_name()
    if not node_name:
        raise Exception("Unable to retrieve node name. Was the cluster created successfully?")

    set_environment(settings["DEPLOY_TO"])

    create_namespace(settings)

    # create priority classes - " Priority affects scheduling order of Pods and out-of-resource eviction ordering
    # on the Node.... A PriorityClass is a non-namespaced object .. The higher the value, the higher the priority."
    # (from https://kubernetes.io/docs/concepts/configuration/pod-priority-preemption/#priorityclass)
    run("kubectl create priorityclass medium-priority --value=1000" % settings, errors_to_ignore=["already exists"])
    run("kubectl create priorityclass high-priority --value=10000" % settings, errors_to_ignore=["already exists"])

    # print cluster info
    run("kubectl cluster-info", verbose=True)

    # wait for the cluster to initialize
    for retry_i in range(1, 5):
        try:
            deploy_settings(settings)
            break
        except RuntimeError as e:
            logger.error(("Error when deploying config maps: %(e)s. This sometimes happens when cluster is "
                          "initializing. Retrying...") % locals())
            time.sleep(5)


def deploy_settings(settings):
    """Deploy settings as a config map"""
    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    # write out a ConfigMap file
    configmap_file_path = os.path.join(settings["DEPLOYMENT_TEMP_DIR"], "deploy/kubernetes/all-settings.properties")
    with open(configmap_file_path, "w") as f:
        for key, value in settings.items():
            if value is None:
                continue

            f.write('%s=%s\n' % (key, value))

    create_namespace(settings)

    run("kubectl delete configmap all-settings", errors_to_ignore=["not found"])
    run("kubectl create configmap all-settings --from-file=%(configmap_file_path)s" % locals())
    run("kubectl get configmaps all-settings -o yaml")


def deploy_secrets(settings):
    """Deploys or updates k8s secrets."""

    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    print_separator("secrets")

    create_namespace(settings)

    # deploy secrets
    secret_labels = DEPLOYMENT_TARGET_SECRETS[settings['DEPLOY_TO']]
    for secret_label in secret_labels:
        run("kubectl delete secret {}-secrets".format(secret_label), verbose=False, errors_to_ignore=["not found"])

    for secret_label in secret_labels:
        secret_command = ['kubectl create secret generic {secret_label}-secrets'.format(secret_label=secret_label)]
        secret_command += [
            '--from-file deploy/secrets/{deploy_to_prefix}/{secret_label}/{file}'.format(
                secret_label=secret_label, deploy_to_prefix=settings['DEPLOY_TO_PREFIX'], file=file)
            for file in SECRETS[secret_label]
        ]
        if secret_label == GCLOUD_CLIENT:
            secret_command.append('--from-file deploy/secrets/shared/gcloud/boto')
        run(" ".join(secret_command).format(deploy_to=settings['DEPLOY_TO']), errors_to_ignore=["already exists"])


def deploy_external_elasticsearch_connector(settings):
    deploy_external_connector(settings, "elasticsearch")


def deploy_external_connector(settings, connector_name):
    if connector_name not in ["elasticsearch"]:
        raise ValueError("Invalid connector name: %s" % connector_name)

    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    print_separator("external-%s-connector" % connector_name)

    run(("kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/external-connectors/" % settings) + "external-%(connector_name)s.yaml" % locals())


def deploy_elasticsearch(settings):
    print_separator("elasticsearch")

    docker_build("elasticsearch", settings, ["--build-arg ELASTICSEARCH_SERVICE_PORT=%s" % settings["ELASTICSEARCH_SERVICE_PORT"]])

    _set_elasticsearch_kubernetes_resources()

    # create persistent volumes
    pv_template_path = 'deploy/kubernetes/elasticsearch/persistent-volumes/es-data.yaml'
    disk_names = get_disk_names('es-data', settings)
    for disk_name in disk_names:
        volume_settings = {'DISK_NAME': disk_name}
        volume_settings.update(settings)
        _process_templates(volume_settings, [pv_template_path])
        run('kubectl create -f {}/{}'.format(settings['DEPLOYMENT_TEMP_DIR'], pv_template_path),
            print_command=True, errors_to_ignore=['already exists'])

    deploy_pod("elasticsearch", settings, wait_until_pod_is_running=False)

    wait_for_not_resource(
        'elasticsearch', resource_type='elasticsearch', json_path='{.items[0].status.phase}', invalid_status='Invalid',
        deployment_target=settings["DEPLOY_TO"], verbose_template='elasticsearch status')

    total_pods = 0
    for num_pods in ['ES_DATA_NUM_PODS', 'ES_CLIENT_NUM_PODS', 'ES_MASTER_NUM_PODS', 'ES_LOADING_NUM_PODS']:
        total_pods += settings.get(num_pods, 0)
    for pod_number_i in range(total_pods):
        sleep_until_pod_is_running('elasticsearch', deployment_target=settings["DEPLOY_TO"], pod_number=pod_number_i)
    for pod_number_i in range(total_pods):
        sleep_until_pod_is_ready('elasticsearch', deployment_target=settings["DEPLOY_TO"], pod_number=pod_number_i)

    wait_for_resource(
        'elasticsearch', resource_type='elasticsearch', json_path='{.items[0].status.phase}', expected_status='Ready',
        deployment_target=settings["DEPLOY_TO"], verbose_template='elasticsearch status')

    wait_for_resource(
        'elasticsearch', resource_type='elasticsearch', json_path='{.items[0].status.health}', expected_status='green',
        deployment_target=settings["DEPLOY_TO"], verbose_template='elasticsearch health')

def _set_elasticsearch_kubernetes_resources():
    has_kube_resource = run('kubectl explain elasticsearch', errors_to_ignore=["server doesn't have a resource type"])
    if not has_kube_resource:
        run('kubectl apply -f deploy/kubernetes/elasticsearch/kubernetes-elasticsearch-all-in-one.yaml')

def deploy_postgres(settings):
    print_separator("postgres")

    docker_build("postgres", settings)

    restore_seqr_db_from_backup = settings.get("RESTORE_SEQR_DB_FROM_BACKUP")
    reset_db = settings.get("RESET_DB")

    if reset_db or restore_seqr_db_from_backup:
        # Since pgdata is stored on a persistent volume, redeploying does not get rid of it. If any existing pgdata is
        # present, even if the databases are empty, postgres will not fully re-initialize the database. This is
        # good if you want to keep the data across a deployment, but problematic if you actually need to rest and
        # reinitialize the db. Therefore, when the database needs to be fully reinitialized, delete pgdata
        run_in_pod(get_pod_name("postgres", deployment_target=settings["DEPLOY_TO"]),
                   "rm -rf /var/lib/postgresql/data/pgdata", verbose=True)

    deploy_pod("postgres", settings, wait_until_pod_is_ready=True)

    if restore_seqr_db_from_backup:
        postgres_pod_name = get_pod_name("postgres", deployment_target=settings["DEPLOY_TO"])
        _restore_seqr_db_from_backup(
            postgres_pod_name, restore_seqr_db_from_backup, settings.get("RESTORE_REFERENCE_DB_FROM_BACKUP"))


def deploy_redis(settings):
    print_separator("redis")

    docker_build("redis", settings, ["--build-arg REDIS_SERVICE_PORT=%s" % settings["REDIS_SERVICE_PORT"]])

    deploy_pod("redis", settings, wait_until_pod_is_ready=True)


def deploy_seqr(settings):
    print_separator("seqr")

    if settings["BUILD_DOCKER_IMAGES"]:
        seqr_git_hash = run("git log -1 --pretty=%h", errors_to_ignore=["Not a git repository"])
        seqr_git_hash = (":" + seqr_git_hash.strip()) if seqr_git_hash is not None else ""

        docker_build("seqr",
                     settings,
                     [
                         "--build-arg SEQR_SERVICE_PORT=%s" % settings["SEQR_SERVICE_PORT"],
                         "--build-arg SEQR_UI_DEV_PORT=%s" % settings["SEQR_UI_DEV_PORT"],
                         "-f deploy/docker/seqr/Dockerfile",
                         "-t %(DOCKER_IMAGE_NAME)s" + seqr_git_hash,
                         ]
                     )

    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    restore_seqr_db_from_backup = settings.get("RESTORE_SEQR_DB_FROM_BACKUP")
    reset_db = settings.get("RESET_DB")

    deployment_target = settings["DEPLOY_TO"]
    postgres_pod_name = get_pod_name("postgres", deployment_target=deployment_target)

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("seqr", settings)
    elif reset_db or restore_seqr_db_from_backup:
        seqr_pod_name = get_pod_name('seqr', deployment_target=deployment_target)
        if seqr_pod_name:
            sleep_until_pod_is_running("seqr", deployment_target=deployment_target)

            run_in_pod(seqr_pod_name, "/usr/local/bin/stop_server.sh", verbose=True)

    if reset_db:
        _drop_seqr_db(postgres_pod_name)
    if restore_seqr_db_from_backup:
        _drop_seqr_db(postgres_pod_name)
        _restore_seqr_db_from_backup(postgres_pod_name, restore_seqr_db_from_backup)
    else:
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database seqrdb'",
                   errors_to_ignore=["already exists"],
                   verbose=True,
                   )
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database reference_data_db'",
                   errors_to_ignore=["already exists"],
                   verbose=True,
                   )

    deploy_pod("seqr", settings, wait_until_pod_is_ready=True)


def redeploy_seqr(deployment_target):
    print_separator('re-deploying seqr')

    seqr_pod_name = get_pod_name('seqr', deployment_target=deployment_target)
    if not seqr_pod_name:
        raise ValueError('No seqr pod found, unable to re-deploy')
    sleep_until_pod_is_running('seqr', deployment_target=deployment_target)

    run_in_pod(seqr_pod_name, 'git pull', verbose=True)
    run_in_pod(seqr_pod_name, './manage.py migrate', verbose=True)
    run_in_pod(seqr_pod_name, '/usr/local/bin/restart_server.sh')


def _drop_seqr_db(postgres_pod_name):
    run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database seqrdb'",
               errors_to_ignore=["does not exist"],
               verbose=True,
               )
    run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database reference_data_db'",
               errors_to_ignore=["does not exist"],
               verbose=True,
               )


def _restore_seqr_db_from_backup(postgres_pod_name, seqrdb_backup, reference_data_backup=None):
    run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database seqrdb'", verbose=True)
    run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database reference_data_db'", verbose=True)
    run("kubectl cp '{backup}' {postgres_pod_name}:/root/$(basename {backup})".format(
        postgres_pod_name=postgres_pod_name, backup=seqrdb_backup), verbose=True)
    run_in_pod(
        postgres_pod_name, "/root/restore_database_backup.sh postgres seqrdb /root/$(basename {backup})".format(
            backup=seqrdb_backup), verbose=True)
    run_in_pod(postgres_pod_name, "rm /root/$(basename {backup})".format(backup=seqrdb_backup, verbose=True))

    if reference_data_backup:
        run("kubectl cp '{backup}' {postgres_pod_name}:/root/$(basename {backup})".format(
            postgres_pod_name=postgres_pod_name, backup=reference_data_backup), verbose=True)
        run_in_pod(
            postgres_pod_name, "/root/restore_database_backup.sh postgres reference_data_db /root/$(basename {backup})".format(
                backup=reference_data_backup), verbose=True)
        run_in_pod(postgres_pod_name, "rm /root/$(basename {backup})".format(backup=reference_data_backup, verbose=True))


def deploy_kibana(settings):
    print_separator("kibana")

    docker_build("kibana", settings)

    _set_elasticsearch_kubernetes_resources()

    deploy_pod("kibana", settings, wait_until_pod_is_ready=True)

    wait_for_resource(
        'kibana', resource_type='kibana', json_path='{.items[0].status.health}', expected_status='green',
        deployment_target=settings["DEPLOY_TO"], verbose_template='kibana health')


def deploy_nginx(settings):
    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    print_separator("nginx")
    run("kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/cloud/deploy.yaml" % locals())
    if settings["DELETE_BEFORE_DEPLOY"]:
        run("kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx.yaml" % settings, errors_to_ignore=["not found"])
    run("kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx.yaml" % settings)


def deploy_pipeline_runner(settings):
    print_separator("pipeline_runner")

    docker_build("pipeline-runner", settings, [
        "-f deploy/docker/%(COMPONENT_LABEL)s/Dockerfile",
    ])

    deploy_pod("pipeline-runner", settings, wait_until_pod_is_running=True)


def deploy_kube_scan(settings):
    print_separator("kube-scan")

    if settings["DELETE_BEFORE_DEPLOY"]:
        run("kubectl apply -f https://raw.githubusercontent.com/octarinesec/kube-scan/master/kube-scan.yaml")

        if settings["ONLY_PUSH_TO_REGISTRY"]:
            return

    run("kubectl apply -f https://raw.githubusercontent.com/octarinesec/kube-scan/master/kube-scan.yaml")


def deploy(deployment_target, components, output_dir=None, runtime_settings={}):
    """Deploy one or more components to the kubernetes cluster specified as the deployment_target.

    Args:
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"
            indentifying which cluster to deploy these components to
        components (list): The list of component names to deploy (eg. "postgres", "redis" - each string must be in
            constants.DEPLOYABLE_COMPONENTS). Order doesn't matter.
        output_dir (string): path of directory where to put deployment logs and rendered config files
        runtime_settings (dict): a dictionary of other key-value pairs that override settings file(s) values.
    """
    if not components:
        raise ValueError("components list is empty")

    if components and "init-cluster" not in components:
        check_kubernetes_context(deployment_target)

    settings = prepare_settings_for_deployment(deployment_target, output_dir, runtime_settings)

    # make sure namespace exists
    if "init-cluster" not in components and not runtime_settings.get("ONLY_PUSH_TO_REGISTRY"):
        create_namespace(settings)

    # call deploy_* functions for each component in "components" list, in the order that these components are listed in DEPLOYABLE_COMPONENTS
    for component in DEPLOYABLE_COMPONENTS:
        if component in components:
            # only deploy requested components
            func_name = "deploy_" + component.replace("-", "_")
            f = globals().get(func_name)
            if f is not None:
                f(settings)
            else:
                raise ValueError("'deploy_{}' function not found. Is '{}' a valid component name?".format(func_name, component))

def redeploy(deployment_target, components):
    if not components:
        raise ValueError("components list is empty")

    check_kubernetes_context(deployment_target)

    # call redeploy_* functions for each component in "components" list, in the order that these components are listed in DEPLOYABLE_COMPONENTS
    for component in DEPLOYABLE_COMPONENTS:
        if component in components:
            # only deploy requested components
            func_name = "redeploy_" + component.replace("-", "_")
            f = globals().get(func_name)
            if f is not None:
                f(deployment_target)
            else:
                raise ValueError(
                    "'redeploy_{}' function not found. Is '{}' a valid component name?".format(func_name, component))


def prepare_settings_for_deployment(deployment_target, output_dir, runtime_settings):
    # parse settings files
    settings = collections.OrderedDict()
    load_settings([
        "deploy/kubernetes/shared-settings.yaml",
        "deploy/kubernetes/%(deployment_target)s-settings.yaml" % locals(),
        ], settings)

    settings.update(runtime_settings)

    # make sure all keys are upper-case
    settings = {key.upper(): value for key, value in settings.items()}

    # configure deployment dir
    settings["DEPLOYMENT_TEMP_DIR"] = os.path.join(
        settings["DEPLOYMENT_TEMP_DIR"],
        "deployments/%(TIMESTAMP)s_%(DEPLOY_TO)s" % settings)

    logger.info("==> Settings:\n%s" % pformat(settings))

    # re-configure logging output to write to log
    log_dir = os.path.join(settings["DEPLOYMENT_TEMP_DIR"], "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    log_file_path = os.path.join(log_dir, "deploy.log")
    sh = logging.StreamHandler(open(log_file_path, "w"))
    sh.setLevel(logging.INFO)
    logger.addHandler(sh)
    logger.info("Starting log file: %(log_file_path)s" % locals())

    template_file_paths = glob.glob("deploy/kubernetes/*.yaml") + glob.glob("deploy/kubernetes/*/*.yaml")
    _process_templates(settings, template_file_paths)

    return settings


def _process_templates(settings, template_file_paths):
    # process Jinja templates to replace template variables with values from settings. Write results to temp output directory.
    input_base_dir = settings["BASE_DIR"]
    output_base_dir = settings["DEPLOYMENT_TEMP_DIR"]
    for file_path in template_file_paths:
        process_jinja_template(input_base_dir, file_path, settings, output_base_dir)

def print_separator(label):
    message = "       DEPLOY %s       " % (label,)
    logger.info("=" * len(message))
    logger.info(message)
    logger.info("=" * len(message) + "\n")


def create_namespace(settings):
    run("kubectl create -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/namespace.yaml" % settings, errors_to_ignore=["already exists"])

    # switch kubectl to use the new namespace
    run("kubectl config set-context $(kubectl config current-context) --namespace=%(NAMESPACE)s" % settings)


def _init_cluster_gcloud(settings):
    """Starts and configures a kubernetes cluster on Google Container Engine based on parameters in settings"""

    run("gcloud config set project %(GCLOUD_PROJECT)s" % settings)

    # create private network so that dataproc jobs can connect to GKE cluster nodes
    # based on: https://medium.com/@DazWilkin/gkes-cluster-ipv4-cidr-flag-69d25884a558
    create_vpc(gcloud_project="%(GCLOUD_PROJECT)s" % settings, network_name="%(GCLOUD_PROJECT)s-auto-vpc" % settings)

    # create cluster
    run(" ".join([
        "gcloud beta container clusters create %(CLUSTER_NAME)s",
        "--enable-autorepair",
        "--enable-autoupgrade",
        "--maintenance-window 7:00",
        "--enable-stackdriver-kubernetes",
        "--cluster-version %(KUBERNETES_VERSION)s",  # to get available versions, run: gcloud container get-server-config
        "--project %(GCLOUD_PROJECT)s",
        "--zone %(GCLOUD_ZONE)s",
        "--machine-type %(CLUSTER_MACHINE_TYPE)s",
        "--num-nodes 1",
        "--no-enable-legacy-authorization",
        "--metadata disable-legacy-endpoints=true",
        "--no-enable-basic-auth",
        "--no-enable-legacy-authorization",
        "--no-issue-client-certificate",
        "--enable-master-authorized-networks",
        "--master-authorized-networks %(MASTER_AUTHORIZED_NETWORKS)s",
        #"--network %(GCLOUD_PROJECT)s-auto-vpc",
        #"--local-ssd-count 1",
        "--scopes", "https://www.googleapis.com/auth/devstorage.read_write",
    ]) % settings, verbose=False, errors_to_ignore=["Already exists"])

    # create cluster nodes - breaking them up into node pools of several machines each.
    # This way, the cluster can be scaled up and down when needed using the technique in
    #    https://github.com/mattsolo1/gnomadjs/blob/master/cluster/elasticsearch/Makefile#L23
    #
    i = 0
    num_nodes_remaining_to_create = int(settings["CLUSTER_NUM_NODES"]) - 1
    num_nodes_per_node_pool = int(settings["NUM_NODES_PER_NODE_POOL"])
    while num_nodes_remaining_to_create > 0:
        i += 1
        command = [
            "gcloud container node-pools create %(CLUSTER_NAME)s-"+str(i),
            "--cluster %(CLUSTER_NAME)s",
            "--project %(GCLOUD_PROJECT)s",
            "--zone %(GCLOUD_ZONE)s",
            "--machine-type %(CLUSTER_MACHINE_TYPE)s",
            "--node-version %(KUBERNETES_VERSION)s",
            #"--no-enable-legacy-authorization",
            "--enable-autorepair",
            "--enable-autoupgrade",
            "--num-nodes %s" % min(num_nodes_per_node_pool, num_nodes_remaining_to_create),
            #"--network %(GCLOUD_PROJECT)s-auto-vpc",
            #"--local-ssd-count 1",
            "--scopes", "https://www.googleapis.com/auth/devstorage.read_write"
        ]
        if settings.get('CLUSTER_NODE_LABELS'):
            command += ['--node-labels', settings['CLUSTER_NODE_LABELS']]
        run(" ".join(command) % settings, verbose=False, errors_to_ignore=["lready exists"])

        num_nodes_remaining_to_create -= num_nodes_per_node_pool

    run(" ".join([
        "gcloud container clusters get-credentials %(CLUSTER_NAME)s",
        "--project %(GCLOUD_PROJECT)s",
        "--zone %(GCLOUD_ZONE)s",
    ]) % settings)

    _init_gcloud_disks(settings)

def _init_gcloud_disks(settings):
    for disk_label in [d.strip() for d in settings['DISKS'].split(',') if d]:
        setting_prefix = disk_label.upper().replace('-', '_')

        disk_names = get_disk_names(disk_label, settings)

        snapshots = [d.strip() for d in settings.get('{}_SNAPSHOTS'.format(setting_prefix), '').split(',') if d]
        if snapshots and len(snapshots) != len(disk_names):
            raise Exception('Invalid configuration for {}: {} disks to create and {} snapshots'.format(
                disk_label, len(disk_names), len(snapshots)
            ))

        for i, disk_name in enumerate(disk_names):
            command = [
                'gcloud compute disks create', disk_name, '--zone', settings['GCLOUD_ZONE'],
            ]
            if settings.get('{}_DISK_TYPE'.format(setting_prefix)):
                command += ['--type', settings['{}_DISK_TYPE'.format(setting_prefix)]]
            if snapshots:
                command += ['--source-snapshot', snapshots[i]]
            else:
                command += ['--size', str(settings['{}_DISK_SIZE'.format(setting_prefix)])]

            run(' '.join(command), verbose=True, errors_to_ignore=['lready exists'])


def docker_build(component_label, settings, custom_build_args=()):
    params = dict(settings)   # make a copy before modifying
    params["COMPONENT_LABEL"] = component_label
    params["DOCKER_IMAGE_NAME"] = "%(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s" % params

    docker_tags = set([
        "",
        ":latest",
        ":%(TIMESTAMP)s" % settings,
        ])

    if settings.get("DOCKER_IMAGE_TAG"):
        docker_tags.add(params["DOCKER_IMAGE_TAG"])

    if not settings["BUILD_DOCKER_IMAGES"]:
        logger.info("Skipping docker build step. Use --build-docker-image to build a new image (and --force to build from the beginning)")
    else:
        docker_build_command = ""
        docker_build_command += "docker build deploy/docker/%(COMPONENT_LABEL)s/ "
        docker_build_command += (" ".join(custom_build_args) + " ")
        if settings["FORCE_BUILD_DOCKER_IMAGES"]:
            docker_build_command += "--no-cache "

        for tag in docker_tags:
            docker_image_name_with_tag = params["DOCKER_IMAGE_NAME"] + tag
            docker_build_command += "-t %(docker_image_name_with_tag)s " % locals()

        run(docker_build_command % params, verbose=True)

    if settings["PUSH_TO_REGISTRY"]:
        for tag in docker_tags:
            docker_image_name_with_tag = params["DOCKER_IMAGE_NAME"] + tag
            docker_push_command = ""
            docker_push_command += "docker push %(docker_image_name_with_tag)s" % locals()
            run(docker_push_command, verbose=True)
            logger.info("==> Finished uploading image: %(docker_image_name_with_tag)s" % locals())


def deploy_pod(component_label, settings, wait_until_pod_is_running=True, wait_until_pod_is_ready=False):
    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod(component_label, settings)

    run(" ".join([
        "kubectl apply",
        "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+component_label+".%(DEPLOY_TO_PREFIX)s.yaml"
    ]) % settings)

    if wait_until_pod_is_running:
        sleep_until_pod_is_running(component_label, deployment_target=settings["DEPLOY_TO"])

    if wait_until_pod_is_ready:
        sleep_until_pod_is_ready(component_label, deployment_target=settings["DEPLOY_TO"])


def delete_pod(component_label, settings, custom_yaml_filename=None):
    deployment_target = settings["DEPLOY_TO"]

    yaml_filename = custom_yaml_filename or (component_label+".%(DEPLOY_TO_PREFIX)s.yaml")

    if is_pod_running(component_label, deployment_target):
        run(" ".join([
            "kubectl delete",
            "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+yaml_filename,
            ]) % settings, errors_to_ignore=["not found"])

    logger.info("waiting for \"%s\" to exit Running status" % component_label)
    while is_pod_running(component_label, deployment_target):
        time.sleep(5)


def create_vpc(gcloud_project, network_name):
    run(" ".join([
        #"gcloud compute networks create seqr-project-custom-vpc --project=%(GCLOUD_PROJECT)s --mode=custom"
        "gcloud compute networks create %(network_name)s",
        "--project=%(gcloud_project)s",
        "--subnet-mode=auto"
    ]) % locals(), errors_to_ignore=["already exists"])

    # add recommended firewall rules to enable ssh, etc.
    run(" ".join([
        "gcloud compute firewall-rules create custom-vpc-allow-tcp-udp-icmp",
        "--project %(gcloud_project)s",
        "--network %(network_name)s",
        "--allow tcp,udp,icmp",
        "--source-ranges 10.0.0.0/8",
    ]) % locals(), errors_to_ignore=["already exists"])

    run(" ".join([
        "gcloud compute firewall-rules create custom-vpc-allow-ports",
        "--project %(gcloud_project)s",
        "--network %(network_name)s",
        "--allow tcp:22,tcp:3389,icmp",
        "--source-ranges 10.0.0.0/8",
    ]) % locals(), errors_to_ignore=["already exists"])
