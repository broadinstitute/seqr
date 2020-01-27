import collections
import glob
import logging
import multiprocessing
import os
from pprint import pformat

import tempfile
import psutil
import time
import sys

from deploy.servctl_utils.other_command_utils import check_kubernetes_context, set_environment
from hail_elasticsearch_pipelines.kubernetes.kubectl_utils import is_pod_running, get_pod_name, get_node_name, run_in_pod, \
    wait_until_pod_is_running as sleep_until_pod_is_running, wait_until_pod_is_ready as sleep_until_pod_is_ready
from hail_elasticsearch_pipelines.kubernetes.yaml_settings_utils import process_jinja_template, load_settings
from seqr.utils.shell_utils import run

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


DEPLOYABLE_COMPONENTS = [
    "init-cluster",
    "settings",
    "secrets",

    "external-elasticsearch-connector",

    "elasticsearch",  # a single elasticsearch instance
    "postgres",
    "redis",
    "phenotips",
    "seqr",
    "kibana",
    "nginx",
    "pipeline-runner",

    "kube-scan",

    # components of a sharded elasticsearch cluster based on https://github.com/pires/kubernetes-elasticsearch-cluster
    "es-client",
    "es-master",
    "es-data",
    "es-kibana",
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
    "phenotips",
    "seqr",
    #"pipeline-runner",
    "kube-scan",
]


DEPLOYMENT_TARGETS["gcloud-dev"] = DEPLOYMENT_TARGETS["gcloud-prod"]
#"gcloud-prod-elasticsearch",
DEPLOYMENT_TARGETS["gcloud-prod-es"] = [
    "init-cluster",
    "settings",
    "es-master",
    "es-client",
    "es-data",
    "es-kibana",
    "kube-scan",
]


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
    for secret_label in [
        "seqr-secrets",
        "postgres-secrets",
        "nginx-secrets",
        "matchbox-secrets",
        "gcloud-client-secrets"
    ]:
        run("kubectl delete secret %(secret_label)s" % locals(), verbose=False, errors_to_ignore=["not found"])

    run(" ".join([
        "kubectl create secret generic seqr-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/seqr/omim_key",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/seqr/postmark_server_token",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/seqr/slack_token",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/seqr/django_key",
    ]) % settings, errors_to_ignore=["already exists"])

    run(" ".join([
        "kubectl create secret generic postgres-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/postgres/postgres.username",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/postgres/postgres.password",
    ]) % settings, errors_to_ignore=["already exists"])

    run(" ".join([
        "kubectl create secret generic nginx-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/nginx-%(DEPLOY_TO)s/tls.key",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/nginx-%(DEPLOY_TO)s/tls.crt",
    ]) % settings, errors_to_ignore=["already exists"])

    run(" ".join([
        "kubectl create secret generic matchbox-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/matchbox/config.json",
    ]) % settings, errors_to_ignore=["already exists"])

    account_key_path = "deploy/secrets/%(DEPLOY_TO_PREFIX)s/gcloud-client/service-account-key.json" % settings
    if not os.path.isfile(account_key_path):
        account_key_path = "deploy/secrets/shared/gcloud/service-account-key.json"
    if os.path.isfile(account_key_path):
        run(" ".join([
            "kubectl create secret generic gcloud-client-secrets",
            "--from-file %(account_key_path)s",
            "--from-file deploy/secrets/shared/gcloud/boto",
        ]) % {'account_key_path': account_key_path}, errors_to_ignore=["already exists"])
    else:
        run(" ".join([
            "kubectl create secret generic gcloud-client-secrets"   # create an empty set of client secrets
        ]), errors_to_ignore=["already exists"])


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

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("elasticsearch", settings)

    docker_build("elasticsearch", settings, ["--build-arg ELASTICSEARCH_SERVICE_PORT=%s" % settings["ELASTICSEARCH_SERVICE_PORT"]])

    deploy_pod("elasticsearch", settings, wait_until_pod_is_ready=True)


def deploy_postgres(settings):
    print_separator("postgres")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("postgres", settings)

    docker_build("postgres", settings)

    deploy_pod("postgres", settings, wait_until_pod_is_ready=True)


def deploy_redis(settings):
    print_separator("redis")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("redis", settings)

    docker_build("redis", settings, ["--build-arg REDIS_SERVICE_PORT=%s" % settings["REDIS_SERVICE_PORT"]])

    deploy_pod("redis", settings, wait_until_pod_is_ready=True)


def deploy_phenotips(settings):
    print_separator("phenotips")

    phenotips_service_port = settings["PHENOTIPS_SERVICE_PORT"]
    restore_phenotips_db_from_backup = settings.get("RESTORE_PHENOTIPS_DB_FROM_BACKUP")
    reset_db = settings.get("RESET_DB")

    deployment_target = settings["DEPLOY_TO"]

    if reset_db or restore_phenotips_db_from_backup:
        delete_pod("phenotips", settings)
        run_in_pod("postgres", "psql -U postgres postgres -c 'drop database xwiki'" % locals(),
           verbose=True,
            errors_to_ignore=["does not exist"],
            deployment_target=deployment_target,
        )
    elif settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("phenotips", settings)

    # init postgres
    if not settings["ONLY_PUSH_TO_REGISTRY"]:
        run_in_pod("postgres",
            "psql -U postgres postgres -c \"create role xwiki with CREATEDB LOGIN PASSWORD 'xwiki'\"" % locals(),
            verbose=True,
            errors_to_ignore=["already exists"],
            deployment_target=deployment_target,
        )

        run_in_pod("postgres",
            "psql -U xwiki postgres -c 'create database xwiki'" % locals(),
            verbose=True,
            errors_to_ignore=["already exists"],
            deployment_target=deployment_target,
        )

        run_in_pod("postgres",
            "psql -U postgres postgres -c 'grant all privileges on database xwiki to xwiki'" % locals(),
        )

    # build container
    docker_build("phenotips", settings, ["--build-arg PHENOTIPS_SERVICE_PORT=%s" % phenotips_service_port])

    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    deploy_pod("phenotips", settings, wait_until_pod_is_ready=True)

    for i in range(0, 3):
        # opening the PhenoTips website for the 1st time triggers a final set of initialization
        # steps which take ~ 1 minute, so run wget to trigger this

        try:
            run_in_pod("phenotips",
                #command="wget http://localhost:%(phenotips_service_port)s -O test.html" % locals(),
                command="curl --verbose -L -u Admin:admin http://localhost:%(phenotips_service_port)s -o test.html" % locals(),
                verbose=True
            )
        except Exception as e:
            logger.error(str(e))

        if i < 2:
            logger.info("Waiting for phenotips to start up...")
            time.sleep(10)

    if restore_phenotips_db_from_backup:
        delete_pod("phenotips", settings)

        postgres_pod_name = get_pod_name("postgres", deployment_target=deployment_target)

        run("kubectl cp '%(restore_phenotips_db_from_backup)s' %(postgres_pod_name)s:/root/$(basename %(restore_phenotips_db_from_backup)s)" % locals(), verbose=True)
        run_in_pod("postgres", "/root/restore_database_backup.sh  xwiki  xwiki  /root/$(basename %(restore_phenotips_db_from_backup)s)" % locals(), deployment_target=deployment_target, verbose=True)
        run_in_pod("postgres", "rm /root/$(basename %(restore_phenotips_db_from_backup)s)" % locals(), deployment_target=deployment_target, verbose=True)

        deploy_pod("phenotips", settings, wait_until_pod_is_ready=True)


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
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database seqrdb'",
                   errors_to_ignore=["does not exist"],
                   verbose=True,
                   )
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database reference_data_db'",
                   errors_to_ignore=["does not exist"],
                   verbose=True,
                   )

    if restore_seqr_db_from_backup:
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database seqrdb'",
                   errors_to_ignore=["does not exist"],
                   verbose=True,
                   )
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database reference_data_db'",
                   errors_to_ignore=["does not exist"],
                   verbose=True,
                   )
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database seqrdb'", verbose=True)
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database reference_data_db'", verbose=True)
        run("kubectl cp '%(restore_seqr_db_from_backup)s' %(postgres_pod_name)s:/root/$(basename %(restore_seqr_db_from_backup)s)" % locals(), verbose=True)
        run_in_pod(postgres_pod_name, "/root/restore_database_backup.sh postgres seqrdb /root/$(basename %(restore_seqr_db_from_backup)s)" % locals(), verbose=True)
        run_in_pod(postgres_pod_name, "rm /root/$(basename %(restore_seqr_db_from_backup)s)" % locals(), verbose=True)
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


def deploy_kibana(settings):
    print_separator("kibana")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("kibana", settings)

    docker_build("kibana", settings, ["--build-arg KIBANA_SERVICE_PORT=%s" % settings["KIBANA_SERVICE_PORT"]])

    deploy_pod("kibana", settings, wait_until_pod_is_ready=True)


def deploy_nginx(settings):
    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    print_separator("nginx")

    run("kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/mandatory.yaml" % locals())

    if settings["DELETE_BEFORE_DEPLOY"]:
        run("kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx.yaml" % settings, errors_to_ignore=["not found"])
    run("kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx.yaml" % settings)


def deploy_kibana(settings):
    print_separator("kibana")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("kibana", settings)

    docker_build("kibana", settings, ["--build-arg KIBANA_SERVICE_PORT=%s" % settings["KIBANA_SERVICE_PORT"]])

    deploy_pod("kibana", settings, wait_until_pod_is_ready=True)


def deploy_pipeline_runner(settings):
    print_separator("pipeline_runner")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("pipeline-runner", settings)

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


def deploy_es_client(settings):
    deploy_elasticsearch_sharded(settings, "es-client")


def deploy_es_master(settings):
    deploy_elasticsearch_sharded(settings, "es-master")


def deploy_es_data(settings):
    deploy_elasticsearch_sharded(settings, "es-data")


def deploy_es_kibana(settings):
    deploy_elasticsearch_sharded(settings, "es-kibana")


def deploy_elasticsearch_sharded(settings, component):
    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    print_separator(component)

    if component == "es-master":
        config_files = [
            "%(DEPLOYMENT_TEMP_DIR)s/hail_elasticsearch_pipelines/kubernetes/elasticsearch-sharded/es-discovery-svc.yaml",
            "%(DEPLOYMENT_TEMP_DIR)s/hail_elasticsearch_pipelines/kubernetes/elasticsearch-sharded/es-master.yaml",
        ]
    elif component == "es-client":
        config_files = [
            "%(DEPLOYMENT_TEMP_DIR)s/hail_elasticsearch_pipelines/kubernetes/elasticsearch-sharded/es-svc.yaml",
            "%(DEPLOYMENT_TEMP_DIR)s/hail_elasticsearch_pipelines/kubernetes/elasticsearch-sharded/es-client.yaml",
        ]
    elif component == "es-data":
        config_files = [
            "%(DEPLOYMENT_TEMP_DIR)s/hail_elasticsearch_pipelines/kubernetes/elasticsearch-sharded/es-data-svc.yaml",
            "%(DEPLOYMENT_TEMP_DIR)s/hail_elasticsearch_pipelines/kubernetes/elasticsearch-sharded/es-data-stateful.yaml",
        ]
    elif component == "es-kibana":
        config_files = [
            "%(DEPLOYMENT_TEMP_DIR)s/hail_elasticsearch_pipelines/kubernetes/elasticsearch-sharded/es-kibana.yaml",
        ]
    elif component == "kibana":
        config_files = [
            "%(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/kibana/kibana.%(DEPLOY_TO_PREFIX)s.yaml",
        ]
    else:
        raise ValueError("Unexpected component: " + component)

    if settings["DELETE_BEFORE_DEPLOY"]:
        for config_file in config_files:
            run("kubectl delete -f " + config_file % settings, errors_to_ignore=["not found"])

    for config_file in config_files:
        run("kubectl apply -f " + config_file % settings)

    if component in ["es-client", "es-master", "es-data", "es-kibana"]:
        # wait until all replicas are running
        num_pods = int(settings.get(component.replace("-", "_").upper()+"_NUM_PODS", 1))
        for pod_number_i in range(num_pods):
            sleep_until_pod_is_running(component, deployment_target=settings["DEPLOY_TO"], pod_number=pod_number_i)

    if component == "es-client":
       run("kubectl describe svc elasticsearch")


def deploy(deployment_target, components, output_dir=None, runtime_settings={}):
    """Deploy one or more components to the kubernetes cluster specified as the deployment_target.

    Args:
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"
            indentifying which cluster to deploy these components to
        components (list): The list of component names to deploy (eg. "postgres", "phenotips" - each string must be in
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
    if "init-cluster" not in components:
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

    # process Jinja templates to replace template variables with values from settings. Write results to temp output directory.
    input_base_dir = settings["BASE_DIR"]
    output_base_dir = settings["DEPLOYMENT_TEMP_DIR"]
    template_file_paths = glob.glob("deploy/kubernetes/*.yaml") + \
                          glob.glob("deploy/kubernetes/*/*.yaml") + \
                          glob.glob("hail_elasticsearch_pipelines/kubernetes/elasticsearch-sharded/*.yaml")
    for file_path in template_file_paths:
        process_jinja_template(input_base_dir, file_path, settings, output_base_dir)

    return settings

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
        run(" ".join([
            "gcloud container node-pools create %(CLUSTER_NAME)s-"+str(i),
            "--cluster %(CLUSTER_NAME)s",
            "--project %(GCLOUD_PROJECT)s",
            "--zone %(GCLOUD_ZONE)s",
            "--machine-type %(CLUSTER_MACHINE_TYPE)s",
            "--node-version %(KUBERNETES_VERSION)s",
            "--no-enable-legacy-authorization",
            "--enable-autorepair",
            "--enable-autoupgrade",
            "--num-nodes %s" % min(num_nodes_per_node_pool, num_nodes_remaining_to_create),
            #"--network %(GCLOUD_PROJECT)s-auto-vpc",
            #"--local-ssd-count 1",
            "--scopes", "https://www.googleapis.com/auth/devstorage.read_write"
        ]) % settings, verbose=False, errors_to_ignore=["lready exists"])

        num_nodes_remaining_to_create -= num_nodes_per_node_pool

    run(" ".join([
        "gcloud container clusters get-credentials %(CLUSTER_NAME)s",
        "--project %(GCLOUD_PROJECT)s",
        "--zone %(GCLOUD_ZONE)s",
    ]) % settings)

    # create disks from snapshots
    created_disks = []
    for i, snapshot_name in enumerate([d.strip() for d in settings.get("CREATE_FROM_SNAPSHOTS", "").split(",") if d]):
        disk_name = "es-data-%d" % (i+1)
        run(" ".join([
            "gcloud compute disks create " + disk_name,
            "--zone %(GCLOUD_ZONE)s",
            "--type pd-ssd",
            "--source-snapshot " + snapshot_name,
        ]) % settings, errors_to_ignore=["lready exists"])

        created_disks.append(disk_name)

    if created_disks:
        settings["CREATE_WITH_EXISTING_DISKS"] = ",".join(created_disks)

    # create PersistentVolume objects for disk
    namespace = settings["NAMESPACE"]
    for i, existing_disk_name in enumerate([d.strip() for d in settings.get("CREATE_WITH_EXISTING_DISKS", "").split(",") if d]):
        file_path = None
        existing_disk_name = existing_disk_name.strip()
        elasticsearch_disk_size = settings["ELASTICSEARCH_DISK_SIZE"]
        with tempfile.NamedTemporaryFile("w") as f:
            f.write("""apiVersion: v1
kind: PersistentVolume
metadata:
  name: %(existing_disk_name)s
  namespace: %(namespace)s
spec:
  capacity:
    storage: %(elasticsearch_disk_size)s
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ssd-storage-class
  gcePersistentDisk:
    fsType: ext4
    pdName: %(existing_disk_name)s
""" % locals())
            f.flush()
            file_path = f.name
            run("kubectl create -f %(file_path)s"  % locals(), print_command=True, errors_to_ignore=["already exists"])

    # create elasticsearch disks storage class
    #run(" ".join([
    #    "kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch/ssd-storage-class.yaml" % settings,
    #]))

    #run(" ".join([
    #    "gcloud compute disks create %(CLUSTER_NAME)s-elasticsearch-disk-0  --type=pd-ssd --zone=us-central1-b --size=%(ELASTICSEARCH_DISK_SIZE)sGi" % settings,
    #]), errors_to_ignore=["already exists"])

    #run(" ".join([
    #    "kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch/es-persistent-volume.yaml" % settings,
    #]))


    # if cluster was already created previously, update its size to match CLUSTER_NUM_NODES
    #run(" ".join([
    #    "gcloud container clusters resize %(CLUSTER_NAME)s --size %(CLUSTER_NUM_NODES)s" % settings,
    #]), is_interactive=True)

    # create persistent disks
    for label in ("postgres", "seqr-static-files"):
        run(" ".join([
            "gcloud compute disks create",
            "--zone %(GCLOUD_ZONE)s",
            "--size %("+label.upper().replace("-", "_")+"_DISK_SIZE)s",
            "%(CLUSTER_NAME)s-"+label+"-disk",
            ]) % settings, verbose=True, errors_to_ignore=["already exists"])


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


def _get_component_group_to_component_name_mapping():
    result = {
        "elasticsearch-sharded": ["es-master", "es-client", "es-data"],
    }
    return result


def resolve_component_groups(deployment_target, components_or_groups):
    component_groups = _get_component_group_to_component_name_mapping()

    return [
        component
        for component_or_group in components_or_groups
        for component in component_groups.get(component_or_group, [component_or_group])
    ]


COMPONENT_GROUP_NAMES = list(_get_component_group_to_component_name_mapping().keys())

