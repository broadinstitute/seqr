import collections
from threading import Thread

import io
import jinja2
import logging
import os
import subprocess
import sys
import time
import yaml

from deploy.utils.constants import COMPONENT_PORTS, COMPONENTS_TO_OPEN_IN_BROWSER
from deploy.utils.kubectl_utils import get_pod_name, get_service_name, \
    run_in_pod, get_pod_status, get_node_name
from seqr.utils.shell_utils import run, wait_for, run_in_background

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_component_port_pairs(components=[]):
    """Uses the PORTS dictionary to return a list of (<component name>, <port>) pairs (For example:
    [('postgres', 5432), ('seqr', 8000), ('seqr', 3000), ... ])

    Args:
        components (list): optional list of component names. If not specified, all components will be included.
    Returns:
        list of components
    """
    if not components:
        components = list(COMPONENT_PORTS.keys())

    return [(component, port) for component in components for port in COMPONENT_PORTS[component]]


def load_settings(settings_file_paths, settings=None, secrets=False):
    """Reads and parses the yaml settings file(s) and returns a dictionary of settings.
    These yaml files are treated as jinja templates. If a settings dictionary is also provided
    as an argument, it will be used as context for jinja template processing.

    Args:
        settings_file_paths (list): a list of yaml settings file paths to load
        settings (dict): optional dictionary of settings files
        secrets (bool): if False, the settings files are assumed to be yaml key-value pairs.
            if True, the files are parsed as Kubernetes Secrets files with base64-encoded values
    Return:
        dict: settings file containing all settings parsed from the given settings file
    """

    if settings is None:
        settings = collections.OrderedDict()

    for settings_path in settings_file_paths:
        with io.open(settings_path, encoding="UTF-8") as settings_file:
            try:
                settings_file_contents = settings_file.read()
                yaml_string = jinja2.Template(settings_file_contents).render(settings)
            except TypeError as e:
                raise ValueError('unable to render file: %(e)s' % locals())

            try:
                loaded_settings = yaml.load(yaml_string)
            except yaml.parser.ParserError as e:
                raise ValueError('unable to parse yaml file %(settings_path)s: %(e)s' % locals())

            if not loaded_settings:
                raise ValueError('yaml file %(settings_path)s appears to be empty' % locals())

            logger.info("Parsed %3d settings from %s" % (len(loaded_settings), settings_path))

            settings.update(loaded_settings)

    return settings


def render(input_base_dir, relative_file_path, settings, output_base_dir):
    """Calls the given render_func to convert the input file + settings dict to a rendered in-memory
    config which it then writes out to the output directory.

    Args:
        input_base_dir (string): The base directory for input file paths.
        relative_file_path (string): template file path relative to base_dir
        settings (dict): dictionary of key-value pairs for resolving any variables in the config template
        output_base_dir (string): The rendered config will be written to the file  {output_base_dir}/{relative_file_path}
    """

    input_file_path = os.path.join(input_base_dir, relative_file_path)
    with io.open(input_file_path, encoding="UTF-8") as istream:
        try:
            rendered_string = jinja2.Template(istream.read()).render(settings)
        except TypeError as e:
            raise ValueError('unable to render file: %(e)s' % locals())

    logger.info("Parsed %s" % relative_file_path)

    output_file_path = os.path.join(output_base_dir, relative_file_path)
    output_dir_path = os.path.dirname(output_file_path)

    if not os.path.isdir(output_dir_path):
        os.makedirs(output_dir_path)

    with open(output_file_path, 'w') as ostream:
        ostream.write(rendered_string)

    #os.chmod(output_file_path, 0x777)
    logger.info("-- wrote out %s" % output_file_path)


def retrieve_settings(deployment_target):
    settings = collections.OrderedDict()

    settings['HOME'] = os.path.expanduser("~")
    settings['TIMESTAMP'] = time.strftime("%Y%m%d_%H%M%S")

    load_settings([
        "deploy/kubernetes/shared-settings.yaml",
        "deploy/kubernetes/%(deployment_target)s-settings.yaml" % locals(),
    ], settings)

    return settings


def check_kubernetes_context(deployment_target, set_if_different=False):
    """
    Make sure the environment is configured correctly, so that kubectl and other commands
    are actually aimed at the given deployment target and not some other cluster.

    Args:
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
        set_if_different (bool): Update the context if the deployment_target doesn't match the current context.
    Return:
        string: The output of `kubectl config current-context`
    """
    try:
        cmd = 'kubectl config current-context'
        kubectl_current_context = subprocess.check_output(cmd, shell=True).strip()
    except subprocess.CalledProcessError as e:
        logger.error('Error while running "kubectl config current-context": %s', e)
        return

    context_is_different = False
    if deployment_target in ["minikube", "kube-solo"]:
        if (deployment_target == "minikube" and kubectl_current_context != "minikube") or (
            deployment_target == "kube-solo" and kubectl_current_context != "kube-solo"):
            logger.error((
                 "'%(cmd)s' returned '%(kubectl_current_context)s'. For %(deployment_target)s deployment, this is "
                 "expected to be '%(deployment_target)s'. Please configure your shell environment "
                 "to point to a local %(deployment_target)s cluster") % locals())
            context_is_different = True

    elif deployment_target.startswith("gcloud"):
        suffix = "-%s" % deployment_target.split("-")[-1]  # "dev" or "prod"
        if not kubectl_current_context.startswith('gke_') or suffix not in kubectl_current_context:
            logger.error(("'%(cmd)s' returned '%(kubectl_current_context)s' which doesn't match %(deployment_target)s. "
                          "To fix this, run:\n\n   "
                          "gcloud container clusters get-credentials <cluster-name>\n\n"
                          "Using one of these clusters: " + subprocess.check_output("gcloud container clusters list", shell=True) +
                          "\n\n") % locals())
            context_is_different = True
    else:
        raise ValueError("Unexpected value for deployment_target: %s" % deployment_target)

    if context_is_different:
        if set_if_different:
            set_environment(deployment_target)
        else:
            sys.exit(-1)

    return kubectl_current_context


def show_status():
    """Print status of various docker and kubernetes subsystems"""

    #run("docker info")
    #run("docker images")
    run("kubectl cluster-info", ignore_all_errors=True)
    #run("kubectl config view | grep 'username\|password'", ignore_all_errors=True)

    logger.info("==> Node IPs - for connecting to Kibana and elasticsearch via NodePorts 30002 and 30001:")
    run("kubectl describe nodes  | grep 'Name:\|ExternalIP'", ignore_all_errors=True)
    logger.info("==> elasticearch client IPs that hail can export to:")
    run("kubectl describe svc elasticsearch  | grep 'Name:\|Endpoints'", ignore_all_errors=True)

    run("kubectl get nodes", ignore_all_errors=True)
    run("kubectl get services", ignore_all_errors=True)
    run("kubectl get pods", ignore_all_errors=True)
    run("kubectl config current-context", ignore_all_errors=True)


def show_dashboard():
    """Opens the kubernetes dashboard in a new browser window"""

    p = run_in_background('kubectl proxy')
    run('open http://localhost:8001/ui')
    p.wait()


def print_log(components, deployment_target, enable_stream_log, wait=True):
    """Executes kubernetes command to print logs for the given pod.

    Args:
        components (list): one or more kubernetes pod labels (eg. 'phenotips' or 'nginx').
            If more than one is specified, logs will be printed from all components in parallel.
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
        enable_stream_log (bool): whether to continuously stream the log instead of just printing
            the log up to now.
        wait (bool): If False, this method will return without waiting for the log streaming process
            to finish printing all logs.

    Returns:
        (list): Popen process objects for the kubectl port-forward processes.
    """
    stream_arg = "-f" if enable_stream_log else ""

    procs = []
    for component_label in components:

        while get_pod_status(component_label, deployment_target) != "Running":
            time.sleep(5)

        pod_name = get_pod_name(component_label, deployment_target=deployment_target)

        p = run_in_background("kubectl logs %(stream_arg)s %(pod_name)s" % locals())
        def print_command_log():
            for line in iter(p.stdout.readline, ''):
                logger.info(line.strip('\n'))

        t = Thread(target=print_command_log)
        t.start()
        procs.append(p)

    if wait:
        wait_for(procs)

    return procs


def set_environment(deployment_target):
    """Configure the shell environment to point to the given deployment_target.

    Args:
        deployment_target (string): "minikube", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """
    if deployment_target.startswith("gcloud"):
        settings = retrieve_settings(deployment_target)

        os.environ["KUBECONFIG"] = os.path.expanduser("~/.kube/config")
        run("gcloud config set core/project %(GCLOUD_PROJECT)s" % settings, print_command=True)
        run("gcloud config set compute/zone %(GCLOUD_ZONE)s" % settings, print_command=True)
        run("gcloud container clusters get-credentials --zone=%(GCLOUD_ZONE)s %(CLUSTER_NAME)s" % settings, print_command=True)
    elif deployment_target == "minikube":
        run("kubectl config use-context minikube", print_command=True)
    elif deployment_target == "kube-solo":
        os.environ["KUBECONFIG"] = os.path.expanduser("~/kube-solo/kube/kubeconfig")
    else:
        raise ValueError("Unexpected deployment_target value: %s" % (deployment_target,))


def port_forward(component_port_pairs=[], deployment_target=None, wait=True, open_browser=False, use_kubectl_proxy=False):
    """Executes kubectl command to forward traffic between localhost and the given pod.
    While this is running, connecting to localhost:<port> will be the same as connecting to that port
    from the pod's internal network.

    Args:
        component_port_pairs (list): 2-tuple(s) containing keyword to use for looking up a kubernetes
            pod, along with the port to forward to that pod (eg. ('mongo', 27017), or ('phenotips', 8080))
        deployment_target (string): "minikube", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
        wait (bool): Whether to block indefinitely as long as the forwarding process is running.
        open_browser (bool): If component_port_pairs includes components that have an http server
            (eg. "seqr" or "phenotips"), then open a web browser window to the forwarded port.
        use_kubectl_proxy (bool): Whether to use kubectl proxy instead of kubectl port-forward
            (see https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster/#manually-constructing-apiserver-proxy-urls)
    Returns:
        (list): Popen process objects for the kubectl port-forward processes.
    """
    procs = []
    for component_label, port in component_port_pairs:
        while get_pod_status(component_label, deployment_target) != "Running":
            time.sleep(5)

        logger.info("Forwarding port %s for %s" % (port, component_label))
        pod_name = get_pod_name(component_label, deployment_target=deployment_target)

        if use_kubectl_proxy:
            command = "kubectl proxy --port 8001"
        else:
            command = "kubectl port-forward %(pod_name)s %(port)s" % locals()

        p = run_in_background(command)

        if open_browser and component_label in COMPONENTS_TO_OPEN_IN_BROWSER:
            if use_kubectl_proxy:
                url = "http://localhost:8001/api/v1/namespaces/default/services/%(component_label)s:%(port)s/proxy/" % locals()
            else:
                url = "http://localhost:%s" % port

            os.system("open " + url)

        procs.append(p)

    if wait:
        wait_for(procs)

    return procs


def troubleshoot_component(component, deployment_target):
    """Runs kubectl command to print detailed debug output for the given component.

    Args:
        component (string): component label (eg. "postgres")
        deployment_target (string): "minikube", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """

    pod_name = get_pod_name(component, deployment_target=deployment_target)

    run("kubectl get pods -o yaml %(pod_name)s" % locals(), verbose=True)


def delete_component(component, deployment_target=None):
    """Runs kubectl commands to delete any running deployment, service, or pod objects for the
    given component(s).

    Args:
        component (string): component to delete (eg. 'phenotips' or 'nginx').
        deployment_target (string): "minikube", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """
    if component == "cockpit":
        run("kubectl delete rc cockpit", errors_to_ignore=["not found"])
    elif component == "es-data":
        run("kubectl delete StatefulSet es-data", errors_to_ignore=["not found"])
    elif component == "nginx":
        run("kubectl delete rc nginx-ingress-rc", errors_to_ignore=["not found"])

    run("kubectl delete deployments %(component)s" % locals(), errors_to_ignore=["not found"])
    run("kubectl delete services %(component)s" % locals(), errors_to_ignore=["not found"])

    pod_name = get_pod_name(component, deployment_target=deployment_target)
    if pod_name:
        run("kubectl delete pods %(pod_name)s" % locals(), errors_to_ignore=["not found"])

    run("kubectl get services" % locals())
    run("kubectl get pods" % locals())


def reset_database(database=[], deployment_target=None):
    """Runs kubectl commands to delete and reset the given database(s).

    Args:
        component (list): one more database labels - "seqrdb", "phenotipsdb", "mongodb"
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """
    if "seqrdb" in database:
        postgres_pod_name = get_pod_name("postgres", deployment_target=deployment_target)
        if not postgres_pod_name:
            logger.error("postgres pod must be running")
        else:
            run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database seqrdb'" % locals(), errors_to_ignore=["does not exist"])
            run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database seqrdb'" % locals())

    if "phenotipsdb" in database:
        postgres_pod_name = get_pod_name("postgres", deployment_target=deployment_target)
        if not postgres_pod_name:
            logger.error("postgres pod must be running")
        else:
            run_in_pod(postgres_pod_name, "psql -U xwiki postgres -c 'drop database xwiki'" % locals(), errors_to_ignore=["does not exist"])
            run_in_pod(postgres_pod_name, "psql -U xwiki postgres -c 'create database xwiki'" % locals())
            #run("kubectl exec %(postgres_pod_name)s -- psql -U postgres xwiki < data/init_phenotipsdb.sql" % locals())

    if "mongodb" in database:
        mongo_pod_name = get_pod_name("mongo", deployment_target=deployment_target)
        if not mongo_pod_name:
            logger.error("mongo pod must be running")
        else:
            run_in_pod(mongo_pod_name, "mongo datastore --eval 'db.dropDatabase()'" % locals())


def delete_all(deployment_target):
    """Runs kubectl and gcloud commands to delete the given cluster and all objects in it.

    Args:
        deployment_target (string): "minikube", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS

    """
    settings = {}

    load_settings([
        "deploy/kubernetes/shared-settings.yaml",
        "deploy/kubernetes/%(deployment_target)s-settings.yaml" % locals(),
    ], settings)

    if settings.get("DEPLOY_TO_PREFIX") == "gcloud":
        run("gcloud container clusters delete --project %(GCLOUD_PROJECT)s --zone %(GCLOUD_ZONE)s --no-async %(CLUSTER_NAME)s" % settings, is_interactive=True)

        run("gcloud compute disks delete --zone %(GCLOUD_ZONE)s %(CLUSTER_NAME)s-postgres-disk" % settings, is_interactive=True)
        run("gcloud compute disks delete --zone %(GCLOUD_ZONE)s %(CLUSTER_NAME)s-mongo-disk" % settings, is_interactive=True)
        run("gcloud compute disks delete --zone %(GCLOUD_ZONE)s %(CLUSTER_NAME)s-elasticsearch-disk" % settings, is_interactive=True)
    else:
        run('kubectl delete deployments --all')
        run('kubectl delete replicationcontrollers --all')
        run('kubectl delete services --all')
        run('kubectl delete StatefulSets --all')
        run('kubectl delete pods --all')

        run('docker kill $(docker ps -q)', errors_to_ignore=["requires at least 1 arg"])
        run('docker rmi -f $(docker images -q)', errors_to_ignore=["requires at least 1 arg"])


def create_user(email=None, password=None):
    """Creates a seqr superuser

    Args:
        email (string): if provided, user will be created non-interactively
        password (string): if provided, user will be created non-interactively
    """

    if not email:
        run_in_pod("seqr", "python -u manage.py createsuperuser" % locals(), is_interactive=True)
    else:
        run_in_pod("seqr", """echo "from django.contrib.auth.models import User; if not User.objects.filter(email='%(email)s'): User.objects.create_superuser('%(email)s', '%(email)s', '%(password)s')" | python manage.py shell""" % locals(), print_command=False)
