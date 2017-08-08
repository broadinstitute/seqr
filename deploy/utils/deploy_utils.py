import glob
import logging
import os
import shutil
import time

from deploy.utils.kubectl_utils import get_pod_status, get_pod_name, \
    try_running_shell_command_in_pod, get_node_name, POD_READY_STATUS, POD_RUNNING_STATUS
from settings import BASE_DIR
from seqr.utils.shell_utils import run_shell_command, try_running_shell_command
from deploy.utils.servctl_utils import render, check_kubernetes_context, retrieve_settings

logger = logging.getLogger(__name__)


def deploy(deployment_label, components=None, output_dir=None, other_settings={}):
    """
    Args:
        deployment_label (string): one of the DEPLOYMENT_LABELS  (eg. "local", or "gcloud")
        components (list): If set to component names from constants.DEPLOYABLE_COMPONENTS,
            (eg. "postgres", "phenotips"), only these components will be deployed.  If not set,
            all DEPLOYABLE_COMPONENTS will be deployed in sequence.
        output_dir (string): path of directory where to put deployment logs and rendered config files
        other_settings (dict): a dictionary of other key-value pairs for use during deployment
    """

    check_kubernetes_context(deployment_label)

    # parse settings files
    settings = retrieve_settings(deployment_label)
    settings.update(other_settings)

    # configure deployment dir
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    output_dir = os.path.join(settings["DEPLOYMENT_TEMP_DIR"], "deployments/%(timestamp)s_%(deployment_label)s" % locals())
    settings["DEPLOYMENT_TEMP_DIR"] = output_dir

    # configure logging output
    log_dir = os.path.join(output_dir, "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    log_file_path = os.path.join(log_dir, "deploy.log")
    sh = logging.StreamHandler(open(log_file_path, "w"))
    sh.setLevel(logging.INFO)
    logger.addHandler(sh)
    logger.info("Starting log file: %(log_file_path)s" % locals())

    # upper-case settings keys
    for key, value in settings.items():
        key = key.upper()
        settings[key] = value
        logger.info("%s = %s" % (key, value))

    # copy settings to output directory
    for file_path in glob.glob("deploy/kubernetes/*.*") + glob.glob("deploy/kubernetes/*/*.*"):
        file_path = file_path.replace('deploy/kubernetes/', '')
        input_base_dir = os.path.join(BASE_DIR, 'deploy/kubernetes')
        output_base_dir = os.path.join(output_dir, 'deploy/kubernetes')
        render(input_base_dir, file_path, settings, output_base_dir)

    for file_path in glob.glob(os.path.join("deploy/kubernetes/*.yaml")):
        try:
            os.makedirs(os.path.join(output_dir, os.path.dirname(file_path)))
        except OSError as e:
            # ignore if the error is that the directory already exists
            # TODO after switch to python3, use exist_ok arg
            if "File exists" not in str(e):
                raise

        shutil.copy(file_path, os.path.join(output_dir, file_path))

    # copy docker directory to output directory
    docker_src_dir = os.path.join(BASE_DIR, "deploy/docker/")
    docker_dest_dir = os.path.join(output_dir, "deploy/docker")
    logger.info("Copying %(docker_src_dir)s to %(docker_dest_dir)s" % locals())
    shutil.copytree(docker_src_dir, docker_dest_dir)

    # copy secrets directory
    secrets_src_dir = os.path.join(BASE_DIR, "deploy/secrets/%(deployment_label)s" % locals())
    secrets_dest_dir = os.path.join(output_dir, "deploy/secrets/%(deployment_label)s" % locals())
    logger.info("Copying %(secrets_src_dir)s to %(secrets_dest_dir)s" % locals())
    shutil.copytree(secrets_src_dir, secrets_dest_dir)

    # deploy
    deploy_init(settings)

    if not components or "mongo" in components:
        deploy_mongo(settings)
    if not components or "postgres" in components:
        deploy_postgres(settings)
    if not components or "phenotips" in components:
        deploy_phenotips(settings)
    #if "matchbox" in components:
    #   deploy_matchbox(settings)
    if not components or "seqr" in components:
        deploy_seqr(settings)
    #if "pipeline-runner" in components:
    #    deploy_pipeline_runner(settings)
    if not components or "elasticsearch" in components:
        deploy_elasticsearch(settings)
    if not components or "kibana" in components:
        deploy_kibana(settings)
    if not components or "nginx" in components:
        deploy_nginx(settings)
    if not components or "cockpit" in components:
        deploy_cockpit(settings)


def _delete_pod(component_label, settings, async=False):
    deployment_label = settings["DEPLOY_TO"]
    if get_pod_status(component_label, deployment_label) == "Running":
        run_shell_command(" ".join([
            "kubectl delete",
            "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+component_label+".%(DEPLOY_TO_PREFIX)s.yaml"
        ]) % settings)

    while get_pod_status(component_label, deployment_label) == "Running" and not async:
        time.sleep(5)


def _deploy_pod(component_label, settings, wait_until_pod_is_running=True, wait_until_pod_is_ready=False):
    run_shell_command(" ".join([
        "kubectl apply",
        "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+component_label+".%(DEPLOY_TO_PREFIX)s.yaml"
    ]) % settings)

    deployment_label = settings["DEPLOY_TO"]
    while wait_until_pod_is_running and get_pod_status(component_label, deployment_label, status_type=POD_RUNNING_STATUS) != "Running":
        time.sleep(5)

    while wait_until_pod_is_ready and get_pod_status(component_label, deployment_label, status_type=POD_READY_STATUS) != "true":
        time.sleep(5)


def _docker_build(component_label, settings, custom_build_args=[]):
    settings = dict(settings)  # make a copy before modifying
    settings["COMPONENT_LABEL"] = component_label

    run_shell_command(" ".join([
            "docker build"
        ] + custom_build_args + [
            "--no-cache" if settings["BUILD_DOCKER_IMAGE"] else "",
            "-t %(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s",
            "deploy/docker/%(COMPONENT_LABEL)s/",
    ]) % settings, verbose=True)

    run_shell_command(" ".join([
        "docker tag",
            "%(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s",
            "%(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s:%(TIMESTAMP)s",
    ]) % settings)


    if settings.get("DEPLOY_TO_PREFIX") == "gcloud":
        run_shell_command("gcloud docker -- push %(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s:%(TIMESTAMP)s" % settings, verbose=True)


def deploy_mongo(settings):
    print_separator("mongo")

    if settings["DELETE_BEFORE_DEPLOY"]:
        _delete_pod("mongo", settings)

    _docker_build("mongo", settings)

    _deploy_pod("mongo", settings, wait_until_pod_is_running=True)


def deploy_phenotips(settings):
    print_separator("phenotips")

    phenotips_service_port = settings["PHENOTIPS_SERVICE_PORT"]
    restore_phenotips_db_from_backup = settings.get("RESTORE_PHENOTIPS_DB_FROM_BACKUP")
    reset_db = settings.get("RESET_DB")

    deployment_label = settings["DEPLOY_TO"]
    postgres_pod_name = get_pod_name("postgres", deployment_label=deployment_label)

    if reset_db or restore_phenotips_db_from_backup:
        _delete_pod("phenotips", settings)
        try_running_shell_command(
            "kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'drop database xwiki'" % locals(),
            errors_to_ignore=["does not exist"],
            verbose=True
        )
    elif settings["DELETE_BEFORE_DEPLOY"]:
        _delete_pod("phenotips", settings)

    try_running_shell_command_in_pod(postgres_pod_name,
        "psql -U postgres postgres -c \"create role xwiki with CREATEDB LOGIN PASSWORD 'xwiki'\"" % locals(),
        verbose=True,
        errors_to_ignore=["already exists"]
    )

    try_running_shell_command_in_pod(postgres_pod_name,
        "psql -U xwiki postgres -c 'create database xwiki'" % locals(),
        verbose=True,
        errors_to_ignore=["already exists"]
    )

    try_running_shell_command_in_pod(postgres_pod_name,
        "psql -U postgres postgres -c 'grant all privileges on database xwiki to xwiki'" % locals(),
    )

    _docker_build(
        "phenotips",
        settings,
        ["--build-arg PHENOTIPS_SERVICE_PORT=%s" % phenotips_service_port],
    )

    _deploy_pod("phenotips", settings, wait_until_pod_is_ready=True)

    for i in range(0, 3):
        # opening the PhenoTips website for the 1st time triggers a final set of initialization
        # steps which take ~ 1 minute, so run wget to trigger this

        try_running_shell_command_in_pod("phenotips",
            command="wget http://localhost:%(phenotips_service_port)s -O test.html" % locals(),
            errors_to_ignore=["Service Unavailable", "Connection refused"],
            verbose=True
        )
        if i < 2:
            time.sleep(15)

    if restore_phenotips_db_from_backup:
        _delete_pod("phenotips", settings)

        run_shell_command("kubectl cp %(restore_phenotips_db_from_backup)s %(postgres_pod_name)s:/root/$(basename %(restore_phenotips_db_from_backup)s)" % locals())
        run_shell_command("kubectl exec %(postgres_pod_name)s -- /root/restore_database_backup.sh  xwiki  xwiki  /root/$(basename %(restore_phenotips_db_from_backup)s)" % locals())
        run_shell_command("kubectl exec %(postgres_pod_name)s -- rm /root/$(basename %(restore_phenotips_db_from_backup)s)" % locals())

        _deploy_pod("phenotips", settings, wait_until_pod_is_ready=True)


def deploy_matchbox(settings):
    print_separator("matchbox")

    if settings["DELETE_BEFORE_DEPLOY"]:
        _delete_pod("matchbox", settings)

    _docker_build(
        "matchbox",
        settings,
        ["--build-arg MATCHBOX_SERVICE_PORT=%s" % settings["MATCHBOX_SERVICE_PORT"]],
    )

    _deploy_pod("matchbox", settings, wait_until_pod_is_ready=True)


def deploy_postgres(settings):
    print_separator("postgres")

    if settings["DELETE_BEFORE_DEPLOY"]:
        _delete_pod("postgres", settings)

    _docker_build(
        "postgres",
        settings,
    )

    _deploy_pod("postgres", settings, wait_until_pod_is_ready=True)


def deploy_pipeline_runner(settings):
    print_separator("pipeline_runner")

    if settings["DELETE_BEFORE_DEPLOY"]:
        _delete_pod("pipeline-runner", settings)

    _docker_build(
        "pipeline-runner",
        settings,
    )

    _deploy_pod("pipeline-runner", settings, wait_until_pod_is_running=True)


def deploy_elasticsearch(settings):
    print_separator("elasticsearch")

    if settings["DELETE_BEFORE_DEPLOY"]:
        _delete_pod("elasticsearch", settings)

    _docker_build(
        "elasticsearch",
        settings,
        ["--build-arg ELASTICSEARCH_SERVICE_PORT=%s" % settings["ELASTICSEARCH_SERVICE_PORT"]],
    )

    _deploy_pod("elasticsearch", settings, wait_until_pod_is_ready=True)


def deploy_kibana(settings):
    print_separator("kibana")

    if settings["DELETE_BEFORE_DEPLOY"]:
        _delete_pod("kibana", settings)

    _docker_build(
        "kibana",
        settings,
        ["--build-arg KIBANA_SERVICE_PORT=%s" % settings["KIBANA_SERVICE_PORT"]],
    )

    _deploy_pod("kibana", settings, wait_until_pod_is_ready=True)


def deploy_cockpit(settings):
    print_separator("cockpit")

    if settings["DELETE_BEFORE_DEPLOY"]:
        run_shell_command("kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/cockpit/cockpit.yaml" % settings)

    # disable username/password prompt - https://github.com/cockpit-project/cockpit/pull/6921
    run_shell_command(" ".join([
        "kubectl create clusterrolebinding anon-cluster-admin-binding",
            "--clusterrole=cluster-admin",
            "--user=system:anonymous",
    ]))

    run_shell_command("kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/cockpit/cockpit.yaml" % settings)

    # print username, password for logging into cockpit
    run_shell_command("kubectl config view")


def deploy_nginx(settings):
    print_separator("nginx")

    try_running_shell_command(
        "kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-ingress.%(DEPLOY_TO_PREFIX)s.yaml" % settings,
        errors_to_ignore=["\"nginx\" not found"],
    )
    run_shell_command("kubectl create -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-ingress.%(DEPLOY_TO_PREFIX)s.yaml" % settings)

    try_running_shell_command(
        "kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-controller.yaml" % settings,
        errors_to_ignore=["\"nginx\" not found"],
    )
    run_shell_command("kubectl create -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-controller.yaml" % settings)

    if settings["DEPLOY_TO_PREFIX"] == "gcloud":
        try_running_shell_command(
            "kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-service.%(DEPLOY_TO_PREFIX)s.yaml" % settings,
            errors_to_ignore=["\"nginx\" not found"],
        )
        run_shell_command("kubectl create -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-service.%(DEPLOY_TO_PREFIX)s.yaml" % settings)

    deployment_label = settings["DEPLOY_TO"]
    while get_pod_status("nginx", deployment_label=deployment_label) != "Running":
        time.sleep(5)


def deploy_seqr(settings):
    print_separator("seqr")

    _docker_build(
        "seqr",
        settings,
        [
            "--build-arg SEQR_SERVICE_PORT=%s" % settings["SEQR_SERVICE_PORT"],
            "--build-arg SEQR_UI_DEV_PORT=%s" % settings["SEQR_UI_DEV_PORT"],
            "-f deploy/docker/%(COMPONENT_LABEL)s/%(DEPLOY_TO_PREFIX)s/Dockerfile"
        ],
    )

    restore_seqr_db_from_backup = settings["RESTORE_SEQR_DB_FROM_BACKUP"]
    reset_db = settings.get("RESET_DB")

    deployment_label = settings["DEPLOY_TO"]
    postgres_pod_name = get_pod_name("postgres", deployment_label=deployment_label)

    if settings["DELETE_BEFORE_DEPLOY"]:
        _delete_pod("seqr", settings)
    elif reset_db or restore_seqr_db_from_backup:
        seqr_pod_name = get_pod_name('seqr', deployment_label=deployment_label)
        run_shell_command("kubectl exec %(seqr_pod_name)s -- /usr/local/bin/stop_server.sh" % locals())

    if reset_db:
        try_running_shell_command(
            "kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'drop database seqrdb'" % locals(),
            errors_to_ignore=["does not exist"],
        )

    if restore_seqr_db_from_backup:
        try_running_shell_command(
            "kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'drop database seqrdb'" % locals(),
            errors_to_ignore=["does not exist"]
        )
        run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'create database seqrdb'" % locals())
        run_shell_command("kubectl cp %(restore_seqr_db_from_backup)s %(postgres_pod_name)s:/root/$(basename %(restore_seqr_db_from_backup)s)" % locals())
        run_shell_command("kubectl exec %(postgres_pod_name)s -- /root/restore_database_backup.sh postgres seqrdb /root/$(basename %(restore_seqr_db_from_backup)s)" % locals())
        run_shell_command("kubectl exec %(postgres_pod_name)s -- rm /root/$(basename %(restore_seqr_db_from_backup)s)" % locals())
    else:
        try_running_shell_command(
            "kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'create database seqrdb'" % locals(),
            errors_to_ignore=["already exists"]
        )

    _deploy_pod("seqr", settings, wait_until_pod_is_ready=True)


def deploy_init(settings):
    print_separator("init")

    if settings["DEPLOY_TO_PREFIX"] == "gcloud":
        run_shell_command("gcloud config set project %(GCLOUD_PROJECT)s" % settings)

        # create cluster

        try_running_shell_command(" ".join([
            "gcloud container clusters create %(CLUSTER_NAME)s",
            "--project %(GCLOUD_PROJECT)s",
            "--zone %(GCLOUD_ZONE)s",
            "--machine-type %(CLUSTER_MACHINE_TYPE)s",
            "--num-nodes %(CLUSTER_NUM_NODES)s",
        ]) % settings, verbose=False, errors_to_ignore=["already exists"])

        run_shell_command(" ".join([
            "gcloud container clusters get-credentials %(CLUSTER_NAME)s",
            "--project %(GCLOUD_PROJECT)s",
            "--zone %(GCLOUD_ZONE)s",
        ]) % settings)

        # create persistent disks
        for label in ("postgres", "mongo", "elasticsearch"):
            try_running_shell_command(" ".join([
                    "gcloud compute disks create",
                    "--zone %(GCLOUD_ZONE)s",
                    "--size %("+label.upper()+"_DISK_SIZE)s",
                    "%(DEPLOY_TO)s-"+label+"-disk",
                ]) % settings, verbose=False, errors_to_ignore=["already exists"])
    else:
        run_shell_command("mkdir -p %(POSTGRES_DBPATH)s" % settings)
        run_shell_command("mkdir -p %(MONGO_DBPATH)s" % settings)
        run_shell_command("mkdir -p %(ELASTICSEARCH_DBPATH)s" % settings)

    # initialize the VM
    node_name = get_node_name()
    if not node_name:
        raise Exception("Unable to retrieve node name. Was the cluster created successfully?")

    # set VM settings required for elasticsearch
    run_shell_command(" ".join([
        "gcloud compute ssh "+node_name,
        "--zone %(GCLOUD_ZONE)s",
        "--command \"sudo /sbin/sysctl -w vm.max_map_count=4000000\""
    ]) % settings)

    # deploy secrets
    for secret in ["seqr-secrets", "postgres-secrets", "nginx-secrets", "matchbox-secrets"]:
        try_running_shell_command("kubectl delete secret " + secret, verbose=False, errors_to_ignore=["not found"])

    run_shell_command(" ".join([
        "kubectl create secret generic seqr-secrets",
            "--from-file deploy/secrets/%(DEPLOY_TO)s/seqr/django_key",
            "--from-file deploy/secrets/%(DEPLOY_TO)s/seqr/omim_key",
            "--from-file deploy/secrets/%(DEPLOY_TO)s/seqr/postmark_server_token",
    ]) % settings)

    run_shell_command(" ".join([
        "kubectl create secret generic postgres-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/postgres/postgres.username",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/postgres/postgres.password",
    ]) % settings)

    run_shell_command(" ".join([
        "kubectl create secret generic nginx-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/nginx/tls.key",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/nginx/tls.crt",
    ]) % settings)

    run_shell_command(" ".join([
        "kubectl create secret generic matchbox-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/matchbox/application.properties",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/matchbox/config.xml",
    ]) % settings)

    # deploy ConfigMap file so that settings key/values can be added as environment variables in each of the pods
    #with open(os.path.join(output_dir, "deploy/kubernetes/all-settings.properties"), "w") as f:
    #    for key, value in settings.items():
    #        f.write("%s=%s\n" % (key, value))

    #run_shell_command("kubectl delete configmap all-settings")
    #run_shell_command("kubectl create configmap all-settings --from-file=deploy/kubernetes/all-settings.properties")
    #run_shell_command("kubectl get configmaps all-settings -o yaml")

    run_shell_command("kubectl cluster-info", verbose=True)


def print_separator(label):
    message = "       DEPLOY %s       " % str(label)
    logger.info("=" * len(message))
    logger.info(message)
    logger.info("=" * len(message) + "\n")

