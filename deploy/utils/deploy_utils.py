import glob
import logging
import multiprocessing
import os
import psutil
import time
import sys


from deploy.utils.kubectl_utils import get_pod_status, get_pod_name, \
    run_in_pod, get_node_name, POD_READY_STATUS, POD_RUNNING_STATUS
from seqr.utils.shell_utils import run
from deploy.utils.servctl_utils import render, check_kubernetes_context, retrieve_settings, set_environment

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def deploy(deployment_target, components, output_dir=None, runtime_settings={}):
    """Deploy all seqr components to a kubernetes cluster.
    Args:
        deployment_target (string): one of the DEPLOYMENT_TARGETs  (eg. "minikube", or "gcloud")
        components (list): A list of components to be deployed from constants.DEPLOYABLE_COMPONENTS
            (eg. "postgres", "phenotips").
        output_dir (string): path of directory where to put deployment logs and rendered config files
        runtime_settings (dict): a dictionary of other key-value pairs that override settings file(s) values.
    """
    if not components:
        raise ValueError("components list is empty")

    if components and "init-cluster" not in components:
        check_kubernetes_context(deployment_target)

    # parse settings files
    settings = retrieve_settings(deployment_target)
    settings.update(runtime_settings)

    # adjust docker image settings
    if settings["BUILD_DOCKER_IMAGE"] and deployment_target == "minikube":
        # to use images built using the minikube docker daemon, minikube only supports imagePullPolicy = "IfNotPresent"
        # https://github.com/kubernetes/minikube/issues/1395#issuecomment-296581721
        # https://kubernetes.io/docs/setup/minikube/
        settings["IMAGE_PULL_POLICY"] = "IfNotPresent"

    if runtime_settings.get("DOCKER_IMAGE_TAG"):
        settings["DOCKER_IMAGE_TAG"] = ":" + runtime_settings["DOCKER_IMAGE_TAG"]
    elif runtime_settings["BUILD_DOCKER_IMAGE"]:
        settings["DOCKER_IMAGE_TAG"] = ":" + settings["TIMESTAMP"]
    else:
        settings["DOCKER_IMAGE_TAG"] = ":latest"

    logger.info("==> Using docker image tag: %(DOCKER_IMAGE_TAG)s" % settings)

    # configure deployment dir
    settings["DEPLOYMENT_TEMP_DIR"] = os.path.join(
        settings["DEPLOYMENT_TEMP_DIR"],
        "deployments/%(TIMESTAMP)s_%(DEPLOY_TO)s" % settings)

    # configure logging output
    log_dir = os.path.join(settings["DEPLOYMENT_TEMP_DIR"], "logs")
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

    # render Jinja templates and put results in output directory
    for file_path in glob.glob("deploy/kubernetes/*.yaml") + glob.glob("deploy/kubernetes/*/*.yaml"):
        file_path = file_path.replace('deploy/kubernetes/', '')

        input_base_dir = os.path.join(runtime_settings["BASE_DIR"], 'deploy/kubernetes')
        output_base_dir = os.path.join(settings["DEPLOYMENT_TEMP_DIR"], 'deploy/kubernetes')

        render(input_base_dir, file_path, settings, output_base_dir)

    # init cluster
    if "init-cluster" in components:
        deploy_init_cluster(settings)

        for retry_i in range(1, 5):
            try:
                deploy_config_map(settings)
                break
            except RuntimeError as e:
                logger.error(("Error when deploying config maps: %(e)s. This sometimes happens when cluster is "
                              "initializing. Retrying...") % locals())
                time.sleep(5)

    # make sure namespace exists
    create_namespace(settings)

    # deploy components
    if "settings" in components:
        deploy_config_map(settings)

    if "secrets" in components:
        deploy_secrets(settings)

    if "cockpit" in components:
        deploy_cockpit(settings)

    if "external-mongo-connector" in components:
        deploy_external_connector(settings, "mongo")

    if "external-elasticsearch-connector" in components:
        deploy_external_connector(settings, "elasticsearch")

    if "elasticsearch" in components:
        deploy_elasticsearch(settings)

    if "mongo" in components:
        deploy_mongo(settings)

    if "postgres" in components:
        deploy_postgres(settings)

    if "redis" in components:
        deploy_redis(settings)

    if "phenotips" in components:
        deploy_phenotips(settings)

    if "matchbox" in components:
       deploy_matchbox(settings)

    if "seqr" in components:
        deploy_seqr(settings)

    if "kibana" in components:
        deploy_kibana(settings)

    if "es-client" in components:
        deploy_elasticsearch_sharded("es-client", settings)

    if "es-master" in components:
        deploy_elasticsearch_sharded("es-master", settings)

    if "es-data" in components:
        deploy_elasticsearch_sharded("es-data", settings)

    if "es-kibana" in components:
        deploy_elasticsearch_sharded("kibana", settings)

    if "nginx" in components:
        deploy_nginx(settings)

    if "pipeline-runner" in components:
        deploy_pipeline_runner(settings)


def delete_pod(component_label, settings, async=False, custom_yaml_filename=None):
    yaml_filename = custom_yaml_filename or (component_label+".%(DEPLOY_TO_PREFIX)s.yaml")

    deployment_target = settings["DEPLOY_TO"]
    if get_pod_status(component_label, deployment_target) == "Running":
        run(" ".join([
            "kubectl delete",
            "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+yaml_filename,
        ]) % settings, errors_to_ignore=["not found"])

    logger.info("waiting for \"%s\" to exit Running status" % component_label)
    while get_pod_status(component_label, deployment_target) in ["Running", "Terminating"] and not async:
        time.sleep(5)


def _wait_until_pod_is_ready(component_label, deployment_target):
    logger.info("waiting for \"%s\" to complete initialization" % component_label)
    while get_pod_status(component_label, deployment_target, status_type=POD_READY_STATUS) != "true":
        time.sleep(5)


def _deploy_pod(component_label, settings, wait_until_pod_is_running=True, wait_until_pod_is_ready=False):
    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    run(" ".join([
        "kubectl apply",
        "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+component_label+".%(DEPLOY_TO_PREFIX)s.yaml"
    ]) % settings)

    if wait_until_pod_is_running:
        _wait_until_pod_is_running(component_label, deployment_target=settings["DEPLOY_TO"])

    if wait_until_pod_is_ready:
        _wait_until_pod_is_ready(component_label, deployment_target=settings["DEPLOY_TO"])


def docker_build(component_label, settings, custom_build_args=()):
    params = dict(settings)   # make a copy before modifying
    params["COMPONENT_LABEL"] = component_label
    params["DOCKER_IMAGE_NAME"] = "%(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s" % params

    docker_command_prefix = "eval $(minikube docker-env); " if settings["DEPLOY_TO"] == "minikube" else ""

    docker_tags = set([
        "",
        ":latest",
        "%(DOCKER_IMAGE_TAG)s" % params,
    ])

    if not settings["BUILD_DOCKER_IMAGE"]:
        logger.info("Skipping docker build step. Use --build-docker-image to build a new image (and --force to build from the beginning)")
    else:
        docker_build_command = docker_command_prefix
        docker_build_command += "docker build deploy/docker/%(COMPONENT_LABEL)s/ "
        docker_build_command += (" ".join(custom_build_args) + " ")
        if settings["FORCE_BUILD_DOCKER_IMAGE"]:
            docker_build_command += "--no-cache "

        for tag in docker_tags:
            docker_image_name_with_tag = params["DOCKER_IMAGE_NAME"] + tag
            docker_build_command += "-t %(docker_image_name_with_tag)s " % locals()

        run(docker_build_command % params, verbose=True)

    if settings["PUSH_TO_REGISTRY"]:
        for tag in docker_tags:
            docker_image_name_with_tag = params["DOCKER_IMAGE_NAME"] + tag
            docker_push_command = docker_command_prefix
            docker_push_command += "docker push %(docker_image_name_with_tag)s" % locals()
            run(docker_push_command, verbose=True)
            logger.info("==> Finished uploading image: %(docker_image_name_with_tag)s" % locals())


def deploy_mongo(settings):
    print_separator("mongo")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("mongo", settings)

    docker_build("mongo", settings)

    _deploy_pod("mongo", settings, wait_until_pod_is_running=True)


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

    _deploy_pod("phenotips", settings, wait_until_pod_is_ready=True)

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

        _deploy_pod("phenotips", settings, wait_until_pod_is_ready=True)


def deploy_matchbox(settings):
    print_separator("matchbox")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("matchbox", settings)

    docker_build("matchbox", settings, ["--build-arg MATCHBOX_SERVICE_PORT=%s" % settings["MATCHBOX_SERVICE_PORT"]])

    _deploy_pod("matchbox", settings, wait_until_pod_is_ready=True)


def deploy_postgres(settings):
    print_separator("postgres")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("postgres", settings)

    docker_build("postgres", settings)

    _deploy_pod("postgres", settings, wait_until_pod_is_ready=True)


def deploy_redis(settings):
    print_separator("redis")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("redis", settings)

    docker_build("redis", settings, ["--build-arg REDIS_SERVICE_PORT=%s" % settings["REDIS_SERVICE_PORT"]])

    _deploy_pod("redis", settings, wait_until_pod_is_ready=True)


def deploy_elasticsearch(settings):
    print_separator("elasticsearch")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("elasticsearch", settings)

    docker_build("elasticsearch", settings, ["--build-arg ELASTICSEARCH_SERVICE_PORT=%s" % settings["ELASTICSEARCH_SERVICE_PORT"]])

    _deploy_pod("elasticsearch", settings, wait_until_pod_is_ready=True)


def deploy_kibana(settings):
    print_separator("kibana")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("kibana", settings)

    docker_build("kibana", settings, ["--build-arg KIBANA_SERVICE_PORT=%s" % settings["KIBANA_SERVICE_PORT"]])

    _deploy_pod("kibana", settings, wait_until_pod_is_ready=True)


def deploy_cockpit(settings):
    print_separator("cockpit")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("cockpit", settings, custom_yaml_filename="cockpit.yaml")
        #"kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/cockpit/cockpit.yaml" % settings,

    if settings["DEPLOY_TO"] == "minikube":
        # disable username/password prompt - https://github.com/cockpit-project/cockpit/pull/6921
        run(" ".join([
            "kubectl create clusterrolebinding anon-cluster-admin-binding",
                "--clusterrole=cluster-admin",
                "--user=system:anonymous",
        ]), errors_to_ignore=["already exists"])

    run("kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/cockpit/cockpit.yaml" % settings)

    # print username, password for logging into cockpit
    run("kubectl config view")


def deploy_nginx(settings):
    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    print_separator("nginx")

    run("kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/mandatory.yaml" % locals())

    if settings["DELETE_BEFORE_DEPLOY"]:
        run("kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx.yaml" % settings, errors_to_ignore=["not found"])
    run("kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx.yaml" % settings)


def deploy_external_connector(settings, connector_name):
    if connector_name not in ["mongo", "elasticsearch"]:
        raise ValueError("Invalid connector name: %s" % connector_name)

    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    print_separator("external-%s-connector" % connector_name)

    run(("kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/external-connectors/" % settings) + "external-%(connector_name)s.yaml" % locals())


def deploy_seqr(settings):
    print_separator("seqr")

    if settings["BUILD_DOCKER_IMAGE"]:
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
            _wait_until_pod_is_running("seqr", deployment_target=deployment_target)

            run_in_pod(seqr_pod_name, "/usr/local/bin/stop_server.sh", verbose=True)

    if reset_db:
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database seqrdb'",
            errors_to_ignore=["does not exist"],
            verbose=True,
        )

    if restore_seqr_db_from_backup:
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database seqrdb'",
            errors_to_ignore=["does not exist"],
            verbose=True,
        )
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database seqrdb'", verbose=True)
        run("kubectl cp '%(restore_seqr_db_from_backup)s' %(postgres_pod_name)s:/root/$(basename %(restore_seqr_db_from_backup)s)" % locals(), verbose=True)
        run_in_pod(postgres_pod_name, "/root/restore_database_backup.sh postgres seqrdb /root/$(basename %(restore_seqr_db_from_backup)s)" % locals(), verbose=True)
        run_in_pod(postgres_pod_name, "rm /root/$(basename %(restore_seqr_db_from_backup)s)" % locals(), verbose=True)
    else:
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database seqrdb'",
            errors_to_ignore=["already exists"],
            verbose=True,
        )

    _deploy_pod("seqr", settings, wait_until_pod_is_ready=True)


def deploy_pipeline_runner(settings):
    print_separator("pipeline_runner")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("pipeline-runner", settings)

    docker_build("pipeline-runner", settings, [ "-f deploy/docker/%(COMPONENT_LABEL)s/Dockerfile" ])

    _deploy_pod("pipeline-runner", settings, wait_until_pod_is_running=True)


def deploy_init_cluster(settings):
    """Provisions a GKE cluster, persistent disks, and any other prerequisites for deployment."""

    print_separator("init-cluster")

    # initialize the VM
    if settings["DEPLOY_TO_PREFIX"] == "gcloud":
        run("gcloud config set project %(GCLOUD_PROJECT)s" % settings)

        # create private network so that dataproc jobs can connect to GKE cluster nodes
        # based on: https://medium.com/@DazWilkin/gkes-cluster-ipv4-cidr-flag-69d25884a558
        create_vpc(gcloud_project="%(GCLOUD_PROJECT)s" % settings, network_name="%(GCLOUD_PROJECT)s-auto-vpc" % settings)

        # create cluster
        run(" ".join([
            "gcloud container clusters create %(CLUSTER_NAME)s",
            "--project %(GCLOUD_PROJECT)s",
            "--zone %(GCLOUD_ZONE)s",
            "--machine-type %(CLUSTER_MACHINE_TYPE)s",
            "--num-nodes 1",
            #"--network %(GCLOUD_PROJECT)s-auto-vpc",
            #"--local-ssd-count 1",
            "--scopes", "https://www.googleapis.com/auth/devstorage.read_write"
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
                "--num-nodes %s" % min(num_nodes_per_node_pool, num_nodes_remaining_to_create),
                #"--network %(GCLOUD_PROJECT)s-auto-vpc",
                #"--local-ssd-count 1",
                "--scopes", "https://www.googleapis.com/auth/devstorage.read_write"
            ]) % settings, verbose=False, errors_to_ignore=["already exists"])

            num_nodes_remaining_to_create -= num_nodes_per_node_pool

        run(" ".join([
            "gcloud container clusters get-credentials %(CLUSTER_NAME)s",
            "--project %(GCLOUD_PROJECT)s",
            "--zone %(GCLOUD_ZONE)s",
        ]) % settings)

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
        for label in ("postgres",): # "mongo"): # , "elasticsearch-sharded"):  # "elasticsearch"
            run(" ".join([
                    "gcloud compute disks create",
                    "--zone %(GCLOUD_ZONE)s",
                    "--size %("+label.upper().replace("-", "_")+"_DISK_SIZE)s",
                    "%(CLUSTER_NAME)s-"+label+"-disk",
                ]) % settings, verbose=True, errors_to_ignore=["already exists"])

    elif settings["DEPLOY_TO"] == "minikube":
        # start minikube if it's not running already
        try:
            status = run("minikube status")
        except Exception as e:
            #run("minikube delete", ignore_all_errors=True)
            if "MINIKUBE_MEMORY" not in settings:
                settings["MINIKUBE_MEMORY"] = str((psutil.virtual_memory().total - 4*10**9) / 10**6)  # leave 4Gb overhead
            if "MINIKUBE_NUM_CPUS" not in settings:
                settings["MINIKUBE_NUM_CPUS"] = multiprocessing.cpu_count()  # use all CPUs on machine

            logger.info("minikube status: %s" % str(e))
            logger.info("starting minikube: ")
            if sys.platform.startswith('darwin'):
                run("minikube stop", ignore_all_errors=True)
                run("minikube start "
                    "--vm-driver=xhyve "  # haven't switched to hyperkit yet because it still has issues like https://bunnyyiu.github.io/2018-07-16-minikube-reboot/
                    "--disk-size=%(MINIKUBE_DISK_SIZE)s "
                    "--memory=%(MINIKUBE_MEMORY)s "
                    "--cpus=%(MINIKUBE_NUM_CPUS)s " % settings)
                # --mount-string %(LOCAL_DATA_DIR)s:%(MINIKUBE_DATA_DIR)s --mount

            elif sys.platform.startswith('linux'):
                logger.info("Please run 'sudo minikube start --vm-driver=none' first and make sure 'minikube status' shows that minikube is running")
                sys.exit(0)
            else:
                logger.warn("We don't test minikube on operating system: %s" % sys.platform)
                run("minikube start "
                    "--vm-driver=virtualbox "
                    "--disk-size=%(MINIKUBE_DISK_SIZE)s "
                    "--memory=%(MINIKUBE_MEMORY)s "
                    "--cpus=%(MINIKUBE_NUM_CPUS)s " % settings)

        run("gcloud auth configure-docker --quiet")

        # this fixes time sync issues on MacOSX which could interfere with token auth (https://github.com/kubernetes/minikube/issues/1378)
        run("minikube ssh -- docker run -i --rm --privileged --pid=host debian nsenter -t 1 -m -u -n -i date -u $(date -u +%m%d%H%M%Y)")

        # set VM max_map_count to the value required for elasticsearch
        run("minikube ssh 'sudo /sbin/sysctl -w vm.max_map_count=262144'")

    else:
        raise ValueError("Unexpected DEPLOY_TO_PREFIX: %(DEPLOY_TO_PREFIX)s" % settings)

    node_name = get_node_name()
    if not node_name:
        raise Exception("Unable to retrieve node name. Was the cluster created successfully?")

    set_environment(settings["DEPLOY_TO"])

    create_namespace(settings)

    # print cluster info
    run("kubectl cluster-info", verbose=True)


def deploy_config_map(settings):
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

    # make sure the
    run("kubectl create -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/namespace.yaml" % settings, errors_to_ignore=["already exists"])

    run(" ".join([
        "kubectl create secret generic seqr-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/seqr/omim_key",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/seqr/postmark_server_token",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/seqr/mme_node_admin_token",
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
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/matchbox/nodes.json",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/matchbox/application.properties",
        "--from-file deploy/secrets/%(DEPLOY_TO_PREFIX)s/matchbox/config.xml",
    ]) % settings, errors_to_ignore=["already exists"])

    if os.path.isfile("deploy/secrets/shared/gcloud/service-account-key.json"):
        run(" ".join([
            "kubectl create secret generic gcloud-client-secrets",
            "--from-file deploy/secrets/shared/gcloud/service-account-key.json",
            "--from-file deploy/secrets/shared/gcloud/boto",
        ]) % settings, errors_to_ignore=["already exists"])
    else:
        run(" ".join([
            "kubectl create secret generic gcloud-client-secrets"   # create an empty set of client secrets
        ]), errors_to_ignore=["already exists"])


def deploy_elasticsearch_sharded(component, settings):
    if settings["ONLY_PUSH_TO_REGISTRY"]:
        return

    print_separator(component)

    if component == "es-master":
        config_files = [
            "%(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch-sharded/es-discovery-svc.yaml",
            "%(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch-sharded/es-master.yaml",
        ]
    elif component == "es-client":
        config_files = [
            "%(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch-sharded/es-svc.yaml",
            "%(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch-sharded/es-client.yaml",
        ]
    elif component == "es-data":
        config_files = [
            "%(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch-sharded/es-data-svc.yaml",
            "%(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch-sharded/es-data-stateful.yaml",
        ]
    elif component == "es-kibana":
        config_files = [
            "%(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch-sharded/kibana-svc.yaml",
            "%(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch-sharded/kibana.yaml",
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

    if component in set(["es-client", "es-master", "es-data", "es-kibana"]):
        # wait until all replicas are running
        num_pods = int(settings.get(component.replace("-", "_").upper()+"_NUM_PODS", 1))
        for pod_number_i in range(num_pods):
            _wait_until_pod_is_running(
                component, deployment_target=settings["DEPLOY_TO"], pod_number=pod_number_i)

    if component == "es-client":
       run("kubectl describe svc elasticsearch")


def _wait_until_pod_is_running(component_label, deployment_target, pod_number=0):
    logger.info("waiting for \"%(component_label)s\" pod #%(pod_number)s to enter Running state" % locals())
    while get_pod_status(component_label, deployment_target, status_type=POD_RUNNING_STATUS, pod_number=pod_number) != "Running":
        time.sleep(5)


def print_separator(label):
    message = "       DEPLOY %s       " % (label,)
    logger.info("=" * len(message))
    logger.info(message)
    logger.info("=" * len(message) + "\n")


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


def create_namespace(settings):
    run("kubectl create -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/namespace.yaml" % settings, errors_to_ignore=["already exists"])

    # switch kubectl to use the new namespace
    run("kubectl config set-context $(kubectl config current-context) --namespace=%(NAMESPACE)s" % settings)
