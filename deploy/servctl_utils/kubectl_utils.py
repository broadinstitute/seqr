import logging
import time

from deploy.servctl_utils.shell_utils import run

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _get_resource_info(
        resource_type="pod",
        labels=None,
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
    labels = labels or {}

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
