import collections
from threading import Thread

import logging
import os
import subprocess
import sys
import time

from deploy.servctl_utils.kubectl_utils import get_pod_name, run_in_pod, wait_until_pod_is_running, is_pod_running, \
    wait_for_resource, get_resource_name
from deploy.servctl_utils.yaml_settings_utils import load_settings
from deploy.servctl_utils.shell_utils import wait_for, run_in_background, run

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


COMPONENT_PORTS = {
    "cockpit":         [9090],

    "elasticsearch":   [9200],
    "kibana":          [5601],

    "redis":           [6379],

    "postgres":        [5432],
    "seqr":            [8000],
    "pipeline-runner": [30005],

    'kube-scan':       [8080],
    #"nginx":           [80, 443],
}


COMPONENTS_TO_OPEN_IN_BROWSER = set([
    "cockpit",
    "elasticsearch",
    "kibana",
    "seqr",
    "pipeline-runner",  # python notebook
])


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

    return [(component, port) for component in components for port in COMPONENT_PORTS.get(component, [])]


def check_kubernetes_context(deployment_target, set_if_different=False):
    """
    Make sure the environment is configured correctly, so that kubectl and other commands
    are actually aimed at the given deployment target and not some other cluster.

    Args:
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"
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
    if deployment_target.startswith("gcloud"):
        suffix = "-%s" % deployment_target.split("-")[1]  # "dev" or "prod"
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
    run("kubectl get deployments --all-namespaces", ignore_all_errors=True)
    run("kubectl get services --all-namespaces", ignore_all_errors=True)
    run("kubectl get pods --all-namespaces", ignore_all_errors=True)
    run("kubectl config current-context", ignore_all_errors=True)


def show_dashboard():
    """Opens the kubernetes dashboard in a new browser window."""

    p = run_in_background('kubectl proxy')
    run('open http://localhost:8001/ui')
    p.wait()


def print_log(components, deployment_target, enable_stream_log, previous=False, wait=True):
    """Executes kubernetes command to print logs for the given pod.

    Args:
        components (list): one or more kubernetes pod labels (eg. 'postgres' or 'nginx').
            If more than one is specified, logs will be printed from all components in parallel.
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev", etc.
        enable_stream_log (bool): whether to continuously stream the log instead of just printing
            the log up to now.
        previous (bool): Prints logs from a previous instance of the container. This is useful for debugging pods that
            don't start or immediately enter crash-loop.
        wait (bool): If False, this method will return without waiting for the log streaming process
            to finish printing all logs.

    Returns:
        (list): Popen process objects for the kubectl port-forward processes.
    """
    stream_arg = "-f" if enable_stream_log else ""
    previous_flag = "--previous" if previous else ""

    procs = []
    for component_label in components:
        if component_label == "kube-scan":
            continue  # See https://github.com/octarinesec/kube-scan for how to connect to the kube-scan pod.

        if not previous:
            wait_until_pod_is_running(component_label, deployment_target)

        pod_name = get_pod_name(component_label, deployment_target=deployment_target)

        p = run_in_background("kubectl logs %(stream_arg)s %(previous_flag)s %(pod_name)s" % locals(), print_command=True)
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
    """Configure the shell environment to point to the given deployment_target using 'gcloud config set-context' and other commands.

    Args:
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev", etc.
    """

    settings = collections.OrderedDict()
    load_settings([
        "deploy/kubernetes/shared-settings.yaml",
        "deploy/kubernetes/%(deployment_target)s-settings.yaml" % locals(),
        ], settings)

    if deployment_target.startswith("gcloud"):
        os.environ["KUBECONFIG"] = os.path.expanduser("~/.kube/config")
        run("gcloud config set core/project %(GCLOUD_PROJECT)s" % settings, print_command=True)
        run("gcloud config set compute/zone %(GCLOUD_ZONE)s" % settings, print_command=True)
        run("gcloud container clusters get-credentials --zone=%(GCLOUD_ZONE)s %(CLUSTER_NAME)s" % settings, print_command=True)
    else:
        raise ValueError("Unexpected deployment_target value: %s" % (deployment_target,))

    run("kubectl config set-context $(kubectl config current-context) --namespace=%(NAMESPACE)s" % settings)


def port_forward(component_port_pairs=[], deployment_target=None, wait=True, open_browser=False, use_kubectl_proxy=False):
    """Executes kubectl command to set up port forwarding between localhost and the given pod.
    While this is running, connecting to localhost:<port> will be the same as connecting to that port
    from the pod's internal network.

    Args:
        component_port_pairs (list): 2-tuple(s) containing keyword to use for looking up a kubernetes
            pod, along with the port to forward to that pod (eg. ('postgres', 5432))
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"
        wait (bool): Whether to block indefinitely as long as the forwarding process is running.
        open_browser (bool): If component_port_pairs includes components that have an http server
            (eg. "seqr" or "postgres"), then open a web browser window to the forwarded port.
        use_kubectl_proxy (bool): Whether to use kubectl proxy instead of kubectl port-forward
            (see https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster/#manually-constructing-apiserver-proxy-urls)
    Returns:
        (list): Popen process objects for the kubectl port-forward processes.
    """
    procs = []
    for component_label, port in component_port_pairs:
        if component_label == "kube-scan":
            continue  # See https://github.com/octarinesec/kube-scan for how to connect to the kube-scan pod.

        wait_until_pod_is_running(component_label, deployment_target)

        logger.info("Forwarding port %s for %s" % (port, component_label))
        if component_label == 'elasticsearch':
            pod_name = 'service/elasticsearch-es-http'
        elif component_label == 'kibana':
            pod_name = 'service/kibana-kb-http'
        else:
            pod_name = get_pod_name(component_label, deployment_target=deployment_target)

        if use_kubectl_proxy:
            command = "kubectl proxy --port 8001"
        else:
            command = 'kubectl port-forward {pod_name} {port}'.format(pod_name=pod_name, port=port)

        p = run_in_background(command)

        if open_browser and component_label in COMPONENTS_TO_OPEN_IN_BROWSER:
            if use_kubectl_proxy:
                url = "http://localhost:8001/api/v1/namespaces/default/services/%(component_label)s:%(port)s/proxy/" % locals()
            else:
                url = "http://localhost:%s" % port

            time.sleep(3)
            os.system("open " + url)

        procs.append(p)

    if wait:
        wait_for(procs)

    return procs


def troubleshoot_component(component, deployment_target):
    """Runs kubectl command to print detailed debug output for the given component.

    Args:
        component (string): component label (eg. "postgres")
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"
    """

    pod_name = get_pod_name(component, deployment_target=deployment_target)

    run("kubectl get pods -o yaml %(pod_name)s" % locals(), verbose=True)


def copy_files_to_or_from_pod(component, deployment_target, source_path, dest_path, direction=1):
    """Copy file(s) to or from the given component.

    Args:
        component (string): component label (eg. "postgres")
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"
        source_path (string): source file path. If copying files to the component, it should be a local path. Otherwise, it should be a file path inside the component pod.
        dest_path (string): destination file path. If copying files from the component, it should be a local path. Otherwise, it should be a file path inside the component pod.
        direction (int): If > 0 the file will be copied to the pod. If < 0, then it will be copied from the pod.
    """
    full_pod_name = get_pod_name(component, deployment_target=deployment_target)
    if not full_pod_name:
        raise ValueError("No '%(pod_name)s' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    if direction < 0:  # copy from pod
        source_path = "%s:%s" % (full_pod_name, source_path)
    elif direction > 0: # copy to pod
        dest_path = "%s:%s" % (full_pod_name, dest_path)

    run("kubectl cp '%(source_path)s' '%(dest_path)s'" % locals())


def open_shell_in_component(component, deployment_target, shell_path='/bin/bash'):
    """Open a command line shell in the given component"""

    run_in_pod(component, shell_path, deployment_target=deployment_target, is_interactive=True)


def delete_component(component, deployment_target=None):
    """Runs kubectl commands to delete any running deployment, service, or pod objects for the given component(s).

    Args:
        component (string): component to delete (eg. 'postgres' or 'nginx').
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"
    """
    if component == "cockpit":
        run("kubectl delete rc cockpit", errors_to_ignore=["not found"])
    elif component == 'elasticsearch':
        run('kubectl delete elasticsearch elasticsearch', errors_to_ignore=['not found'])
        # Deleting a released persistent volume does not delete the data on the underlying disk
        wait_for_resource(
            component, '{.items[0].status.phase}', 'Released', deployment_target=deployment_target, resource_type='pv')
        pv = get_resource_name(component, resource_type='pv', deployment_target=deployment_target)
        while pv:
            run('kubectl delete pv {}'.format(pv))
            pv = get_resource_name(component, resource_type='pv', deployment_target=deployment_target)
    elif component == 'kibana':
        run('kubectl delete kibana kibana', errors_to_ignore=['not found'])
    elif component == "nginx":
        raise ValueError("TODO: implement deleting nginx")

    run("kubectl delete deployments %(component)s" % locals(), errors_to_ignore=["not found"])
    run("kubectl delete services %(component)s" % locals(), errors_to_ignore=["not found"])

    pod_name = get_pod_name(component, deployment_target=deployment_target)
    if pod_name:
        run("kubectl delete pods %(pod_name)s" % locals(), errors_to_ignore=["not found"])

        logger.info("waiting for \"%s\" to exit Running status" % component)
        while is_pod_running(component, deployment_target):
            time.sleep(5)


    # print services and pods status
    run("kubectl get services" % locals(), verbose=True)
    run("kubectl get pods" % locals(), verbose=True)


def reset_database(database=[], deployment_target=None):
    """Runs kubectl commands to delete and reset the given database(s).

    Args:
        component (list): one more database labels - "seqrdb"
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"
    """
    if "seqrdb" in database:
        postgres_pod_name = get_pod_name("postgres", deployment_target=deployment_target)
        if not postgres_pod_name:
            logger.error("postgres pod must be running")
        else:
            run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'drop database seqrdb'" % locals(), errors_to_ignore=["does not exist"])
            run_in_pod(postgres_pod_name, "psql -U postgres postgres -c 'create database seqrdb'" % locals())


def delete_all(deployment_target):
    """Runs kubectl and gcloud commands to delete the given cluster and all objects in it.

    Args:
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"

    """
    settings = {}

    load_settings([
        "deploy/kubernetes/shared-settings.yaml",
        "deploy/kubernetes/%(deployment_target)s-settings.yaml" % locals(),
    ], settings)

    if settings.get("DEPLOY_TO_PREFIX") == "gcloud":
        run("gcloud container clusters delete --project %(GCLOUD_PROJECT)s --zone %(GCLOUD_ZONE)s --no-async %(CLUSTER_NAME)s" % settings, is_interactive=True)

        for disk_label in [d.strip() for d in settings['DISKS'].split(',') if d]:
            for disk_name in  get_disk_names(disk_label, settings):
                run('gcloud compute disks delete --zone {zone} {disk_name}'.format(
                    zone=settings['GCLOUD_ZONE'], disk_name=disk_name), is_interactive=True)
    else:
        run('kubectl delete deployments --all')
        run('kubectl delete replicationcontrollers --all')
        run('kubectl delete services --all')
        run('kubectl delete StatefulSets --all')
        run('kubectl delete pods --all')

        run('docker kill $(docker ps -q)', errors_to_ignore=["requires at least 1 arg"])
        run('docker rmi -f $(docker images -q)', errors_to_ignore=["requires at least 1 arg"])


def get_disk_names(disk, settings):
    num_disks = settings.get('{}_NUM_DISKS'.format(disk.upper().replace('-', '_'))) or 1
    return [
        '{cluster_name}-{disk}-disk{suffix}'.format(
            cluster_name=settings['CLUSTER_NAME'], disk=disk, suffix='-{}'.format(i + 1) if num_disks > 1 else '')
    for i in range(num_disks)]

