import logging
import time

from deploy.servctl_utils.shell_utils import run

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _get_resource_info(
        resource_type="pod",
        labels={},
        json_path="{.items[].metadata.name}",
        errors_to_ignore=("array index out of bounds:",),
        verbose=False,
    ):
    """Runs 'kubectl get <resource_type> -l <label1=value1,label2=value2...> -o jsonpath=<json path>' and returns its output.

    Args:
        resource_type (string): "pod", "service", etc.
        labels (dict): (eg. {'name': 'phenotips'})
        json_path (string): a json path query string (for example, "{.items[*].metadata.name}")
        errors_to_ignore (list):
        verbose (bool):

    Returns:
        (string) kubectl command output (eg. "postgres-410765475-1vtkn") or None if the kubectl command returned nothing
    """

    l_arg = "-l {}".format(",".join(["%s=%s" % (key, value) for key, value in labels.items()])) if labels else ""

    output = run(
        "kubectl get %(resource_type)s %(l_arg)s -o jsonpath=%(json_path)s" % locals(),
        errors_to_ignore=errors_to_ignore,
        print_command=False,
        verbose=verbose,
    )

    return output.strip('\n') if output is not None else None


def _get_resource_status(resource_name, json_path_of_status, deployment_target=None, resource_type='pod', verbose_template='status'):
    """Utility method for looking up a resources's status."""
    labels = {"name": resource_name}
    if deployment_target:
        labels["deployment"] = deployment_target

    result = _get_resource_info(
        labels=labels,
        resource_type=resource_type,
        json_path=json_path_of_status,
        errors_to_ignore=["array index out of bounds: index"],
        verbose=False,
    )

    if verbose_template:
        logger.info('{} = {}'.format(verbose_template, result))

    return result


def is_pod_running(pod_name, deployment_target=None, pod_number=0, verbose=True):
    """Returns True if the given pod is in "Running" state, and False otherwise."""

    json_path = "{.items[%(pod_number)s].status.phase}" % locals()

    verbose_template = None
    if verbose:
        verbose_template = '{}[{}].is_running'.format(pod_name, pod_number)

    status = _get_resource_status(
        pod_name, json_path, deployment_target=deployment_target, verbose_template=verbose_template)

    return status == 'Running'


def is_pod_ready(pod_name, deployment_target=None, pod_number=0, verbose=True):
    """Returns True if the given pod is in "Ready" state, and False otherwise."""

    json_path = "{.items[%(pod_number)s].status.containerStatuses[0].ready}" % locals()

    verbose_template = None
    if verbose:
        verbose_template = '{}[{}].is_ready'.format(pod_name, pod_number)

    status = _get_resource_status(
        pod_name, json_path, deployment_target=deployment_target, verbose_template=verbose_template)

    return status == 'true'


def wait_until_pod_is_running(pod_name, deployment_target=None, pod_number=0):
    """Sleeps until the pod enters "Running" state"""

    logger.info("waiting for \"%s\" pod #%s to enter Running state" % (pod_name, pod_number))
    while not is_pod_running(pod_name, deployment_target, pod_number=pod_number):
        time.sleep(5)


def wait_until_pod_is_ready(pod_name, deployment_target=None, pod_number=0):
    """Sleeps until the pod enters "Ready" state"""

    logger.info("waiting for \"%s\" pod #%s to complete initialization" % (pod_name, pod_number))
    while not is_pod_ready(pod_name, deployment_target, pod_number=pod_number):
        time.sleep(5)


def wait_for_resource(resource_name, json_path, expected_status, deployment_target=None, verbose_template='status', resource_type='pod'):
    """Sleeps until the given resource has the expected status."""
    while expected_status != _get_resource_status(
            resource_name, json_path, deployment_target=deployment_target, verbose_template=verbose_template,
            resource_type=resource_type):
        time.sleep(5)


def wait_for_not_resource(resource_name, json_path, invalid_status, deployment_target=None, verbose_template='status', resource_type='pod'):
    """Sleeps until the given resource does not have the invalid status."""
    status = None
    while not status or status == invalid_status:
        time.sleep(5)
        status =  _get_resource_status(
            resource_name, json_path, deployment_target=deployment_target, verbose_template=verbose_template,
            resource_type=resource_type)


def get_pod_name(pod_name_label, deployment_target=None, pod_number=0):
    """Takes a pod name label (eg. "phenotips") and returns the full pod name (eg. "phenotips-cdd4d7dc9-vgmjx").

    If there are multiple pods with the given label, it returns the 1st one by default.

    Args:
          pod_name_label (string): the "name" label of the pod
          deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "minikube", "gcloud-dev", etc.
          pod_number (int): if there are multiple pods with the given label, it returns this one of the pods.

    Returns:
        string: full name of the pod, or None if such a pod doesn't exist
    """
    return get_resource_name(pod_name_label, 'pod', deployment_target=deployment_target, pod_number=pod_number)


def get_resource_name(name_label, resource_type, deployment_target=None, pod_number=0):
    """Takes a resource label (eg. "phenotips") and returns the full resource name (eg. "phenotips-cdd4d7dc9-vgmjx").

    If there are multiple resources with the given label, it returns the 1st one by default.

    Args:
          name_label (string): the "name" label of the resource
          resource_type (string): the type of the resource - eg. pod
          deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "minikube", "gcloud-dev", etc.
          pod_number (int): if there are multiple pods with the given label, it returns this one of the pods.

    Returns:
        string: full name of the pod, or None if such a pod doesn't exist
    """
    labels = {"name": name_label}
    if deployment_target:
        labels["deployment"] = deployment_target

    return _get_resource_info(
        labels=labels,
        resource_type=resource_type,
        json_path="{.items[%(pod_number)s].metadata.name}" % locals(),
        errors_to_ignore=["array index out of bounds: index 0"],
        verbose=False,
    )


def get_node_name():
    """Returns kubernetes cluster node name. If there are multiple nodes, it returns the 1st one."""

    return _get_resource_info(
        resource_type="nodes",
        json_path="{.items[0].metadata.name}",
        errors_to_ignore=["array index out of bounds: index 0"],
        verbose=True,
    )


def run_in_pod(pod_name, command, deployment_target=None, errors_to_ignore=None, print_command=True, verbose=False, is_interactive=False):
    """Execute an arbitrary linux command inside the given pod. Assumes there's only 1 instance with the given pod_name.

    Args:
        pod_name (str): either the pod's "name" label (eg. 'phenotips' or 'nginx'), or the full pod name (eg. "phenotips-cdd4d7dc9-vgmjx")
        command (str): linux command to execute inside the pod
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "minikube", "gcloud-dev", etc.
        errors_to_ignore (list): if the command's return code isn't in ok_return_codes, but its
            output contains one of the strings in this list, the bad return code will be ignored,
            and this function will return None. Otherwise, it raises a RuntimeException.
        print_command (bool):
        verbose (bool):
        is_interactive (bool): whether the command expects input from the user
    """

    full_pod_name = get_pod_name(pod_name, deployment_target=deployment_target)
    if not full_pod_name:
        # assume it's already a full pod name
        full_pod_name = pod_name

    it_arg = "-it" if is_interactive else ""
    run("kubectl exec %(it_arg)s %(full_pod_name)s -- %(command)s" % locals(),
        errors_to_ignore=errors_to_ignore,
        print_command=print_command,
        verbose=verbose,
        is_interactive=is_interactive)

