import glob
import logging
import os
import time


from deploy.utils.kubectl_utils import get_pod_status, get_pod_name, \
    run_in_pod, get_node_name, POD_READY_STATUS, POD_RUNNING_STATUS
from seqr.utils.shell_utils import run
from deploy.utils.servctl_utils import render, check_kubernetes_context, retrieve_settings

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)



def deploy(deployment_target, components, output_dir=None, other_settings={}):
    """Deploy all seqr components to a kubernetes cluster.
    Args:
        deployment_target (string): one of the DEPLOYMENT_TARGETs  (eg. "local", or "gcloud")
        components (list): A list of components to be deployed from constants.DEPLOYABLE_COMPONENTS
            (eg. "postgres", "phenotips").
        output_dir (string): path of directory where to put deployment logs and rendered config files
        other_settings (dict): a dictionary of other key-value pairs for use during deployment
    """
    if not components:
        raise ValueError("components list is empty")

    if components and "init-cluster" not in components:
        check_kubernetes_context(deployment_target)

    # parse settings files
    settings = retrieve_settings(deployment_target)
    settings.update(other_settings)

    # configure deployment dir
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    output_dir = os.path.join(settings["DEPLOYMENT_TEMP_DIR"], "deployments/%(timestamp)s_%(deployment_target)s" % locals())
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

    # render Jinja templates and put results in output directory
    for file_path in glob.glob("deploy/kubernetes/*.yaml") + glob.glob("deploy/kubernetes/*/*.yaml"):
        file_path = file_path.replace('deploy/kubernetes/', '')

        input_base_dir = os.path.join(other_settings["BASE_DIR"], 'deploy/kubernetes')
        output_base_dir = os.path.join(output_dir, 'deploy/kubernetes')

        render(input_base_dir, file_path, settings, output_base_dir)

    # deploy
    if "init-cluster" in components:
        deploy_init_cluster(settings)

    if "secrets" in components:
        deploy_secrets(settings)

    #if "init-elasticsearch-cluster" in components:
    #    pass

    if "cockpit" in components:
        deploy_cockpit(settings)

    if "mongo" in components:
        deploy_mongo(settings)

    if "postgres" in components:
        deploy_postgres(settings)

    if "phenotips" in components:
        deploy_phenotips(settings)

    if "matchbox" in components:
       deploy_matchbox(settings)

    if "seqr" in components:
        deploy_seqr(settings)

    if "elasticsearch" in components:
        deploy_elasticsearch(settings)

    if "es-client" in components:
        deploy_elasticsearch_sharded("es-client", settings)

    if "es-master" in components:
        deploy_elasticsearch_sharded("es-master", settings)

    if "es-data" in components:
        deploy_elasticsearch_sharded("es-data", settings)

    if "es-kibana" in components:
        deploy_elasticsearch_sharded("kibana", settings)

    if "kibana" in components:
        deploy_kibana(settings)



    #if "pipeline-runner" in components:
    #    deploy_pipeline_runner(settings)

    #if "elasticsearch" in components:
    #    if settings["DEPLOY_TO"] == "local":
    #        deploy_elasticsearch(settings)
    #    else:
    #        deploy_elasticsearch_sharded(settings)

    #if "kibana" in components:
    #    deploy_kibana(settings)

    if "nginx" in components:
        deploy_nginx(settings)


def delete_pod(component_label, settings, async=False, custom_yaml_filename=None):
    yaml_filename = custom_yaml_filename or (component_label+".%(DEPLOY_TO_PREFIX)s.yaml")

    deployment_target = settings["DEPLOY_TO"]
    if get_pod_status(component_label, deployment_target) == "Running":
        run(" ".join([
            "kubectl delete",
            "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+yaml_filename,
        ]) % settings, errors_to_ignore=["not found"])

    logger.info("waiting for \"%s\" to exit Running status" % component_label)
    while get_pod_status(component_label, deployment_target) == "Running" and not async:
        time.sleep(5)


def _wait_until_pod_is_ready(component_label, deployment_target):
    logger.info("waiting for \"%s\" to complete initialization" % component_label)
    while get_pod_status(component_label, deployment_target, status_type=POD_READY_STATUS) != "true":
        time.sleep(5)


def _deploy_pod(component_label, settings, wait_until_pod_is_running=True, wait_until_pod_is_ready=False):
    run(" ".join([
        "kubectl apply",
        "-f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/"+component_label+"/"+component_label+".%(DEPLOY_TO_PREFIX)s.yaml"
    ]) % settings)

    if wait_until_pod_is_running:
        _wait_until_pod_is_running(component_label, deployment_target=settings["DEPLOY_TO"])

    if wait_until_pod_is_ready:
        _wait_until_pod_is_ready(component_label, deployment_target=settings["DEPLOY_TO"])


def docker_build(component_label, settings, custom_build_args=[]):
    settings = dict(settings)  # make a copy before modifying
    settings["COMPONENT_LABEL"] = component_label

    run(" ".join([
            "docker build"
        ] + custom_build_args + [
            "--no-cache" if settings["BUILD_DOCKER_IMAGE"] else "",
            "-t %(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s",
            "deploy/docker/%(COMPONENT_LABEL)s/",
    ]) % settings, verbose=True)

    run(" ".join([
        "docker tag",
            "%(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s",
            "%(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s:%(TIMESTAMP)s",
    ]) % settings)


    if settings.get("DEPLOY_TO_PREFIX") == "gcloud":
        run("gcloud docker -- push %(DOCKER_IMAGE_PREFIX)s/%(COMPONENT_LABEL)s:%(TIMESTAMP)s" % settings, verbose=True)


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

    docker_build(
        "phenotips",
        settings,
        ["--build-arg PHENOTIPS_SERVICE_PORT=%s" % phenotips_service_port],
    )

    _deploy_pod("phenotips", settings, wait_until_pod_is_ready=True)

    for i in range(0, 3):
        # opening the PhenoTips website for the 1st time triggers a final set of initialization
        # steps which take ~ 1 minute, so run wget to trigger this

        try:
            run_in_pod("phenotips",
                command="wget http://localhost:%(phenotips_service_port)s -O test.html" % locals(),
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

        run("kubectl cp %(restore_phenotips_db_from_backup)s %(postgres_pod_name)s:/root/$(basename %(restore_phenotips_db_from_backup)s)" % locals(), verbose=True)
        run_in_pod("postgres", "/root/restore_database_backup.sh  xwiki  xwiki  /root/$(basename %(restore_phenotips_db_from_backup)s)" % locals(), deployment_target=deployment_target, verbose=True)
        run_in_pod("postgres", "rm /root/$(basename %(restore_phenotips_db_from_backup)s)" % locals(), deployment_target=deployment_target, verbose=True)

        _deploy_pod("phenotips", settings, wait_until_pod_is_ready=True)


def deploy_matchbox(settings):
    print_separator("matchbox")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("matchbox", settings)

    docker_build(
        "matchbox",
        settings,
        ["--build-arg MATCHBOX_SERVICE_PORT=%s" % settings["MATCHBOX_SERVICE_PORT"]],
    )

    _deploy_pod("matchbox", settings, wait_until_pod_is_ready=True)


def deploy_postgres(settings):
    print_separator("postgres")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("postgres", settings)

    docker_build(
        "postgres",
        settings,
    )

    _deploy_pod("postgres", settings, wait_until_pod_is_ready=True)


def deploy_pipeline_runner(settings):
    print_separator("pipeline_runner")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("pipeline-runner", settings)

    docker_build(
        "pipeline-runner",
        settings,
    )

    _deploy_pod("pipeline-runner", settings, wait_until_pod_is_running=True)


def deploy_elasticsearch(settings):
    print_separator("elasticsearch")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("elasticsearch", settings)

    docker_build(
        "elasticsearch",
        settings,
        ["--build-arg ELASTICSEARCH_SERVICE_PORT=%s" % settings["ELASTICSEARCH_SERVICE_PORT"]],
    )

    _deploy_pod("elasticsearch", settings, wait_until_pod_is_ready=True)


def deploy_kibana(settings):
    print_separator("kibana")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("kibana", settings)

    docker_build(
        "kibana",
        settings,
        ["--build-arg KIBANA_SERVICE_PORT=%s" % settings["KIBANA_SERVICE_PORT"]],
    )

    _deploy_pod("kibana", settings, wait_until_pod_is_ready=True)


def deploy_cockpit(settings):
    print_separator("cockpit")

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("cockpit", settings, custom_yaml_filename="cockpit.yaml")
        #"kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/cockpit/cockpit.yaml" % settings,

    if settings["DEPLOY_TO"] == "local":
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
    print_separator("nginx")

    run("kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-ingress.%(DEPLOY_TO_PREFIX)s.yaml" % settings,
        errors_to_ignore=["\"nginx\" not found"],
    )
    run("kubectl create -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-ingress.%(DEPLOY_TO_PREFIX)s.yaml" % settings)

    run("kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-controller.yaml" % settings,
        errors_to_ignore=["\"nginx\" not found"],
    )
    run("kubectl create -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-controller.yaml" % settings)

    if settings["DEPLOY_TO_PREFIX"] == "gcloud":
        run("kubectl delete -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-service.%(DEPLOY_TO_PREFIX)s.yaml" % settings,
            errors_to_ignore=["\"nginx\" not found"],
        )
        run("kubectl create -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/nginx/nginx-service.%(DEPLOY_TO_PREFIX)s.yaml" % settings)

    _wait_until_pod_is_running("nginx", deployment_target=settings["DEPLOY_TO"])


def deploy_seqr(settings):
    print_separator("seqr")

    docker_build(
        "seqr",
        settings,
        [
            "--build-arg SEQR_SERVICE_PORT=%s" % settings["SEQR_SERVICE_PORT"],
            "--build-arg SEQR_UI_DEV_PORT=%s" % settings["SEQR_UI_DEV_PORT"],
            "-f deploy/docker/%(COMPONENT_LABEL)s/%(DEPLOY_TO_PREFIX)s/Dockerfile"
        ],
    )

    restore_seqr_db_from_backup = settings.get("RESTORE_SEQR_DB_FROM_BACKUP")
    reset_db = settings.get("RESET_DB")

    deployment_target = settings["DEPLOY_TO"]
    postgres_pod_name = get_pod_name("postgres", deployment_target=deployment_target)

    if settings["DELETE_BEFORE_DEPLOY"]:
        delete_pod("seqr", settings)
    elif reset_db or restore_seqr_db_from_backup:
        _wait_until_pod_is_running("seqr", deployment_target=deployment_target)

        seqr_pod_name = get_pod_name('seqr', deployment_target=deployment_target)
        run_in_pod(seqr_pod_name, "/usr/local/bin/stop_server.sh" % locals(), verbose=True)

    if reset_db:
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database seqrdb'" % locals(),
            errors_to_ignore=["does not exist"],
            verbose=True,
        )

    if restore_seqr_db_from_backup:
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database seqrdb'" % locals(),
            errors_to_ignore=["does not exist"],
            verbose=True,
        )
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database seqrdb'" % locals(), verbose=True)
        run("kubectl cp %(restore_seqr_db_from_backup)s %(postgres_pod_name)s:/root/$(basename %(restore_seqr_db_from_backup)s)" % locals(), verbose=True)
        run_in_pod(postgres_pod_name, "/root/restore_database_backup.sh postgres seqrdb /root/$(basename %(restore_seqr_db_from_backup)s)" % locals(), verbose=True)
        run_in_pod(postgres_pod_name, "rm /root/$(basename %(restore_seqr_db_from_backup)s)" % locals(), verbose=True)
    else:
        run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database seqrdb'" % locals(),
            errors_to_ignore=["already exists"],
            verbose=True,
        )

    _deploy_pod("seqr", settings, wait_until_pod_is_ready=True)


def deploy_init_cluster(settings):
    """Provisions a GKE cluster, persistant disks, and any other prerequisites for deployment."""

    print_separator("init-cluster")

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
        ]) % settings, verbose=False, errors_to_ignore=["already exists"])

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
                "gcloud beta container node-pools create %(CLUSTER_NAME)s-"+str(i),
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

        # create elasticsearch disks
        run(" ".join([
            "kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch/ssd-storage-class.yaml" % settings,
        ]))

        #run(" ".join([
        #    "gcloud compute disks create %(CLUSTER_NAME)s-elasticsearch-disk-0  --type=pd-ssd --zone=us-central1-b --size=%(ELASTICSEARCH_DISK_SIZE)sGi" % settings,
        #]), errors_to_ignore=["already exists"])

        #run(" ".join([
        #    "kubectl apply -f %(DEPLOYMENT_TEMP_DIR)s/deploy/kubernetes/elasticsearch/es-persistent-volume.yaml" % settings,
        #]))


        # if cluster was already created previously, update it's size to match CLUSTER_NUM_NODES
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
    else:
        run("mkdir -p %(POSTGRES_DBPATH)s" % settings)
        run("mkdir -p %(MONGO_DBPATH)s" % settings)
        run("mkdir -p %(ELASTICSEARCH_DBPATH)s" % settings)

    # initialize the VM
    node_name = get_node_name()
    if not node_name:
        raise Exception("Unable to retrieve node name. Was the cluster created successfully?")

    # set VM settings required for elasticsearch
    if settings["DEPLOY_TO"] == "local":
        if node_name == "minikube":
            run("minikube ssh 'sudo /sbin/sysctl -w vm.max_map_count=262144'" % locals())
        elif node_name == "kube-solo":
            run("corectl ssh %(node_name)s \"sudo /sbin/sysctl -w vm.max_map_count=262144\"" % locals())

    #else:
    #    run(" ".join([
    #        "gcloud compute ssh "+node_name,
    #        "--zone %(GCLOUD_ZONE)s",
    #        "--command \"sudo /sbin/sysctl -w vm.max_map_count=262144\""
    #    ]) % settings)

    # deploy ConfigMap file so that settings key/values can be added as environment variables in each of the pods
    #with open(os.path.join(output_dir, "deploy/kubernetes/all-settings.properties"), "w") as f:
    #    for key, value in settings.items():
    #        f.write("%s=%s\n" % (key, value))

    #run("kubectl delete configmap all-settings")
    #run("kubectl create configmap all-settings --from-file=deploy/kubernetes/all-settings.properties")
    #run("kubectl get configmaps all-settings -o yaml")

    run("kubectl cluster-info", verbose=True)


def deploy_secrets(settings):
    """Deploys or updates k8s secrets."""

    print_separator("secrets")

    # deploy secrets
    for secret in ["seqr-secrets", "postgres-secrets", "nginx-secrets", "matchbox-secrets"]:
        run("kubectl delete secret " + secret, verbose=False, errors_to_ignore=["not found"])

    run(" ".join([
        "kubectl create secret generic seqr-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/seqr/django_key",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/seqr/omim_key",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/seqr/postmark_server_token",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/seqr/mme_node_admin_token",
    ]) % settings)

    run(" ".join([
        "kubectl create secret generic postgres-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/postgres/postgres.username",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/postgres/postgres.password",
    ]) % settings)

    run(" ".join([
        "kubectl create secret generic nginx-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/nginx/tls.key",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/nginx/tls.crt",
    ]) % settings)

    run(" ".join([
        "kubectl create secret generic matchbox-secrets",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/matchbox/nodes.json",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/matchbox/application.properties",
        "--from-file deploy/secrets/%(DEPLOY_TO)s/matchbox/config.xml",
    ]) % settings)


def deploy_elasticsearch_sharded(component, settings):
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
        run("kubectl apply -f " + config_file % settings, errors_to_ignore=["already exists"])

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
        "--mode=auto"
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


