import collections
from threading import Thread

import jinja2
import logging
import os
import subprocess
import sys
import time
import yaml

from deploy.utils.constants import COMPONENT_PORTS, COMPONENTS_TO_OPEN_IN_BROWSER
from deploy.utils.kubectl_utils import get_pod_name, get_service_name, \
    run_in_pod, get_pod_status
from seqr.utils.shell_utils import run, wait_for, run_in_background

logger = logging.getLogger(__name__)


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
        with open(settings_path) as settings_file:
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
    with open(input_file_path) as istream:
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
    logger.info("-- wrote rendered output to %s" % output_file_path)


def retrieve_settings(deployment_target):
    settings = collections.OrderedDict()

    settings['HOME'] = os.path.expanduser("~")
    settings['TIMESTAMP'] = time.strftime("%Y%m%d_%H%M%S")
    #settings['SEQR_REPO_PATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))

    load_settings([
        "deploy/kubernetes/shared-settings.yaml",
        "deploy/kubernetes/%(deployment_target)s-settings.yaml" % locals(),
    ], settings)

    return settings


def check_kubernetes_context(deployment_target):
    """
    Make sure the environment is configured correctly, so that kubectl and other commands
    are actually aimed at the given deployment target and not some other cluster.

    Args:
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """
    try:
        cmd = 'kubectl config current-context'
        kubectl_current_context = subprocess.check_output(cmd, shell=True).strip()
    except subprocess.CalledProcessError as e:
        logger.error('Error while running "kubectl config current-context": %s', e)
        #i = raw_input("Continue? [Y/n] ")
        #if i != 'Y' and i != 'y':
        #    sys.exit('Exiting...')
        return

    if deployment_target == "local":
        if kubectl_current_context != 'kube-solo':
            logger.error(("'%(cmd)s' returned '%(kubectl_current_context)s'. For %(deployment_target)s deployment, this is "
                          "expected to equal 'kube-solo'. Please configure your shell environment "
                          "to point to a local kube-solo cluster by installing "
                          "kube-solo from https://github.com/TheNewNormal/kube-solo-osx, starting the kube-solo VM, "
                          "and then clicking on 'Preset OS Shell' in the kube-solo menu to launch a pre-configured shell.") % locals())
            sys.exit(-1)

    elif deployment_target.startswith("gcloud"):
        suffix = deployment_target.split("-")[-1]  # "dev" or "prod"
        if not kubectl_current_context.startswith('gke_') or not kubectl_current_context.endswith(suffix):
            logger.error(("'%(cmd)s' returned '%(kubectl_current_context)s' which doesn't match %(deployment_target)s. "
                          "To fix this, run:\n\n   "
                          "gcloud container clusters get-credentials <cluster-name>\n\n"
                          "Using one of these clusters: " + subprocess.check_output("gcloud container clusters list", shell=True) +
                          "\n\n") % locals())
            sys.exit(-1)
    else:
        raise ValueError("Unexpected value for deployment_target: %s" % deployment_target)


def show_status():
    """Print status of various docker and kubernetes subsystems"""

    run("docker info")
    run("docker images")
    run("kubectl cluster-info")
    run("kubectl config view | grep 'username\|password'")
    run("kubectl get services")
    run("kubectl get pods")
    run("kubectl config current-context")


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
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """
    settings = retrieve_settings(deployment_target)
    run("gcloud config set core/project %(GCLOUD_PROJECT)s" % settings)
    run("gcloud config set compute/zone %(GCLOUD_ZONE)s" % settings)
    run("gcloud container clusters get-credentials --zone=%(GCLOUD_ZONE)s %(CLUSTER_NAME)s" % settings)


def port_forward(component_port_pairs=[], deployment_target=None, wait=True, open_browser=False):
    """Executes kubectl command to forward traffic between localhost and the given pod.
    While this is running, connecting to localhost:<port> will be the same as connecting to that port
    from the pod's internal network.

    Args:
        component_port_pairs (list): 2-tuple(s) containing keyword to use for looking up a kubernetes
            pod, along with the port to forward to that pod (eg. ('mongo', 27017), or ('phenotips', 8080))
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
        wait (bool): Whether to block indefinitely as long as the forwarding process is running.
        open_browser (bool): If component_port_pairs includes components that have an http server
            (eg. "seqr" or "phenotips"), then open a web browser window to the forwarded port.
    Returns:
        (list): Popen process objects for the kubectl port-forward processes.
    """
    procs = []
    for component_label, port in component_port_pairs:
        while get_pod_status(component_label, deployment_target) != "Running":
            time.sleep(5)

        logger.info("Forwarding port %s for %s" % (port, component_label))
        pod_name = get_pod_name(component_label, deployment_target=deployment_target)

        p = run_in_background("kubectl port-forward %(pod_name)s %(port)s" % locals())

        if open_browser and component_label in COMPONENTS_TO_OPEN_IN_BROWSER:
            os.system("open http://localhost:%s" % port)

        procs.append(p)

    if wait:
        wait_for(procs)

    return procs


def troubleshoot_component(component, deployment_target):
    """Runs kubectl command to print detailed debug output for the given component.

    Args:
        component (string): component label (eg. "postgres")
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """

    pod_name = get_pod_name(component, deployment_target=deployment_target)

    run("kubectl get pods -o yaml %(pod_name)s" % locals(), verbose=True)


def kill_component(component, deployment_target=None):
    """Runs kubectl commands to delete any running deployment, service, or pod objects for the
    given component(s).

    Args:
        component (string): component to delete (eg. 'phenotips' or 'nginx').
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """
    if component == "cockpit":
        run("kubectl delete rc cockpit", errors_to_ignore=["not found"])

    run("kubectl delete deployments %(component)s" % locals(), errors_to_ignore=["not found"])
    run("kubectl delete services %(component)s" % locals(), errors_to_ignore=["not found"])
    pod_name = get_pod_name(component, deployment_target=deployment_target)
    if pod_name:
        run("kubectl delete pods %(pod_name)s" % locals(), errors_to_ignore=["not found"])

    if component == "nginx":
        run("kubectl delete rc nginx-ingress-rc" % locals(), errors_to_ignore=["not found"])

    run("kubectl get services" % locals())
    run("kubectl get pods" % locals())


def reset_database(database=[], deployment_target=None):
    """Runs kubectl commands to delete and reset the given database(s).

    Args:
        component (list): one more database labels - "seqrdb", "phenotipsdb", "mongodb"
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """
    if "seqrdb" in database:
        postgres_pod_name = get_pod_name('postgres', deployment_target=deployment_target)
        if not postgres_pod_name:
            logger.error("postgres pod must be running")
        else:
            run("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'drop database seqrdb'" % locals(), errors_to_ignore=["does not exist"])
            run("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'create database seqrdb'" % locals())

    if "phenotipsdb" in database:
        postgres_pod_name = get_pod_name('postgres', deployment_target=deployment_target)
        if not postgres_pod_name:
            logger.error("postgres pod must be running")
        else:
            run("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'drop database xwiki'" % locals(), errors_to_ignore=["does not exist"])
            run("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'create database xwiki'" % locals())
            #run("kubectl exec %(postgres_pod_name)s -- psql -U postgres xwiki < data/init_phenotipsdb.sql" % locals())

    if "mongodb" in database:
        mongo_pod_name = get_pod_name('mongo', deployment_target=deployment_target)
        if not mongo_pod_name:
            logger.error("mongo pod must be running")
        else:
            run("kubectl exec %(mongo_pod_name)s -- mongo datastore --eval 'db.dropDatabase()'" % locals())


def kill_and_delete_all(deployment_target):
    """Runs kubectl and gcloud commands to delete the given cluster and all objects in it.

    Args:
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.

    """
    settings = {}

    load_settings([
        "deploy/kubernetes/shared-settings.yaml",
        "deploy/kubernetes/%(deployment_target)s-settings.yaml" % locals(),
    ], settings)

    run('kubectl delete deployments --all')
    run('kubectl delete replicationcontrollers --all')
    run('kubectl delete services --all')
    run('kubectl delete pods --all')
    run('kubectl delete pods --all')

    if settings["DEPLOY_TO_PREFIX"] == "gcloud":
        run("gcloud container clusters delete --zone %(GCLOUD_ZONE)s --no-async %(CLUSTER_NAME)s" % settings, is_interactive=True)
        run("gcloud compute disks delete --zone %(GCLOUD_ZONE)s %(DEPLOY_TO)s-postgres-disk" % settings, is_interactive=True)
        run("gcloud compute disks delete --zone %(GCLOUD_ZONE)s %(DEPLOY_TO)s-mongo-disk" % settings, is_interactive=True)
        run("gcloud compute disks delete --zone %(GCLOUD_ZONE)s %(DEPLOY_TO)s-elasticsearch-disk" % settings, is_interactive=True)
    else:
        run('docker kill $(docker ps -q)', errors_to_ignore=["requires at least 1 arg"])
        run('docker rmi -f $(docker images -q)', errors_to_ignore=["requires at least 1 arg"])



def create_user(deployment_target):
    """Creates a seqr superuser

    Args:
        deployment_target (string): "local", "gcloud-dev", etc. See constants.DEPLOYMENT_TARGETS.
    """

    run_in_pod("seqr", "python -u manage.py createsuperuser" % locals(), is_interactive=True)
