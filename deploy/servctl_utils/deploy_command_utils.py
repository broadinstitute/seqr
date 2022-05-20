import collections
import glob
import logging
import os
from pprint import pformat
import time

from deploy.servctl_utils.kubectl_utils import is_pod_running, \
    wait_until_pod_is_running as sleep_until_pod_is_running, wait_until_pod_is_ready as sleep_until_pod_is_ready, \
    wait_for_resource, wait_for_not_resource
from deploy.servctl_utils.yaml_settings_utils import process_jinja_template, load_settings
from deploy.servctl_utils.shell_utils import run

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


DEPLOYMENT_ENVS = ['gcloud-prod', 'gcloud-dev']

DEPLOYMENT_TARGETS = [
    "settings",
    "secrets",
    "linkerd",
    "elasticsearch",
    "kibana",
    "redis",
    "seqr",
    "elasticsearch-snapshot-config",
]

# pipeline runner docker image is used by docker-compose for local installs, but isn't part of the Broad seqr deployment
DEPLOYABLE_COMPONENTS = ['pipeline-runner'] + DEPLOYMENT_TARGETS

GCLOUD_CLIENT = 'gcloud-client'

SECRETS = {
    'elasticsearch': ['users', 'users_roles', 'roles.yml'],
    'es-snapshot-gcs': ['{deploy_to}/gcs.client.default.credentials_file'],
    GCLOUD_CLIENT: ['service-account-key.json'],
    'kibana': ['elasticsearch.password'],
    'matchbox': ['{deploy_to}/config.json'],
    'nginx': ['{deploy_to}/tls.key', '{deploy_to}/tls.crt'],
    'postgres': ['{deploy_to}/password'],
    'seqr': [
        'omim_key', 'postmark_server_token', 'slack_token', 'airtable_key', 'django_key', 'seqr_es_password', 'airflow_api_audience',
        '{deploy_to}/google_client_id',  '{deploy_to}/google_client_secret', '{deploy_to}/ga_token_id',
    ],
}


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


def deploy_secrets(settings, components=None):
    """Deploys or updates k8s secrets."""

    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    print_separator("secrets")

    create_namespace(settings)

    if not components:
        components = SECRETS.keys()

    # deploy secrets
    for secret_label in components:
        run("kubectl delete secret {}-secrets".format(secret_label), verbose=False, errors_to_ignore=["not found"])

    for secret_label in components:
        secret_files = SECRETS.get(secret_label)
        if not secret_files:
            raise Exception('Invalid secret component {}'.format(secret_label))

        secret_command = ['kubectl create secret generic {secret_label}-secrets'.format(secret_label=secret_label)]
        secret_command += [
            '--from-file deploy/secrets/gcloud/{secret_label}/{file}'.format(secret_label=secret_label, file=file)
            for file in secret_files
        ]
        if secret_label == GCLOUD_CLIENT:
            secret_command.append('--from-file deploy/secrets/shared/gcloud/boto')
        run(" ".join(secret_command).format(deploy_to=settings['DEPLOY_TO']), errors_to_ignore=["already exists"])


def deploy_elasticsearch(settings):
    print_separator("elasticsearch")

    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    _set_elasticsearch_kubernetes_resources()

    # create persistent volumes
    pv_template_path = 'deploy/kubernetes/elasticsearch/persistent-volumes/es-data.yaml'
    num_disks = settings['ES_DATA_NUM_PODS']
    disk_names = [
        '{cluster_name}-es-data-disk{suffix}'.format(
            cluster_name=settings['CLUSTER_NAME'], suffix='-{}'.format(i + 1) if num_disks > 1 else '')
        for i in range(num_disks)]
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
    has_kube_resource = run('kubectl explain elasticsearch', errors_to_ignore=["server doesn't have a resource type", "couldn't find resource for"])
    if not has_kube_resource:
        run('kubectl create -f https://download.elastic.co/downloads/eck/1.9.1/crds.yaml')
        run('kubectl apply -f https://download.elastic.co/downloads/eck/1.9.1/operator.yaml')


def deploy_elasticsearch_snapshot_config(settings):
    print_separator('elasticsearch snapshot configuration')

    docker_build("curator", settings)

    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    if settings['ES_CONFIGURE_SNAPSHOTS']:
        # run the k8s job to set up the repo
        run('kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch/configure-snapshot-repo.yaml' % settings)
        wait_for_resource(
            'configure-es-snapshot-repo', resource_type='job', json_path='{.items[0].status.conditions[0].type}',
            expected_status='Complete')
        # clean up the job after completion
        run('kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch/configure-snapshot-repo.yaml' % settings)
        # Set up the monthly cron job
        run('kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch/snapshot-cronjob.yaml' % settings)


def deploy_linkerd(settings):
    print_separator('linkerd')

    version_match = run("linkerd version | awk '/Client/ {print $3}'")
    if version_match.strip() != settings["LINKERD_VERSION"]:
        raise Exception("Your locally installed linkerd version does not match %s. "
                        "Download the correct version from https://github.com/linkerd/linkerd2/releases/tag/%s" % \
                        (settings['LINKERD_VERSION'], settings['LINKERD_VERSION']))

    has_namespace = run('kubectl get namespace linkerd', errors_to_ignore=['namespaces "linkerd" not found'])
    if not has_namespace:
        run('linkerd install | kubectl apply -f -')

        run('linkerd check')


def deploy_redis(settings):
    print_separator("redis")

    docker_build("redis", settings, [])

    deploy_pod("redis", settings, wait_until_pod_is_ready=True)


def deploy_seqr(settings):
    print_separator("seqr")

    if settings['BUILD_DOCKER_IMAGES']:
        raise Exception("seqr image docker builds via servctl have been deprecated. Please ensure that your desired "
                        "build has been produced via Cloudbuild and GCR, and then run the deployment without the "
                        "docker build flag.")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("seqr", settings)

    deploy_pod("seqr", settings, wait_until_pod_is_ready=True)


def deploy_kibana(settings):
    print_separator("kibana")

    docker_build("kibana", settings)

    _set_elasticsearch_kubernetes_resources()

    deploy_pod("kibana", settings, wait_until_pod_is_ready=True)

    wait_for_resource(
        'kibana', resource_type='kibana', json_path='{.items[0].status.health}', expected_status='green',
        deployment_target=settings["DEPLOY_TO"], verbose_template='kibana health')


def deploy_pipeline_runner(settings):
    print_separator("pipeline_runner")

    docker_build("pipeline-runner", settings, [
        "-f deploy/docker/%(COMPONENT_LABEL)s/Dockerfile",
    ])


def deploy(deployment_target, components, output_dir=None, runtime_settings=None):
    """Deploy one or more components to the kubernetes cluster specified as the deployment_target.

    Args:
        deployment_target (string): value from DEPLOYMENT_ENVS - eg. "gcloud-dev"
            indentifying which cluster to deploy these components to
        components (list): The list of component names to deploy (eg. "postgres", "redis" - each string must be in
            constants.DEPLOYABLE_COMPONENTS). Order doesn't matter.
        output_dir (string): path of directory where to put deployment logs and rendered config files
        runtime_settings (dict): a dictionary of other key-value pairs that override settings file(s) values.
    """
    runtime_settings = runtime_settings or {}

    if not components:
        raise ValueError("components list is empty")

    if components:
        run('deploy/kubectl_helpers/utils/check_context.sh {}'.format(deployment_target.replace('gcloud-', '')))

    settings = prepare_settings_for_deployment(deployment_target, output_dir, runtime_settings)

    # make sure namespace exists
    if not runtime_settings.get("ONLY_PUSH_TO_REGISTRY"):
        create_namespace(settings)

    if components[0] == 'secrets':
        deploy_secrets(settings, components=components[1:])
        return

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
    if component_label == 'elasticsearch' and settings.get('ELASTICSEARCH_VERSION'):
        docker_tags.add("%(DOCKER_IMAGE_TAG)s-%(ELASTICSEARCH_VERSION)s" % settings)

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
        "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+component_label+".gcloud.yaml"
    ]) % settings)

    if wait_until_pod_is_running:
        sleep_until_pod_is_running(component_label, deployment_target=settings["DEPLOY_TO"])

    if wait_until_pod_is_ready:
        sleep_until_pod_is_ready(component_label, deployment_target=settings["DEPLOY_TO"])


def delete_pod(component_label, settings, custom_yaml_filename=None):
    deployment_target = settings["DEPLOY_TO"]

    yaml_filename = custom_yaml_filename or (component_label+".gcloud.yaml")

    if is_pod_running(component_label, deployment_target):
        run(" ".join([
            "kubectl delete",
            "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+yaml_filename,
            ]) % settings, errors_to_ignore=["not found"])

    logger.info("waiting for \"%s\" to exit Running status" % component_label)
    while is_pod_running(component_label, deployment_target):
        time.sleep(5)
