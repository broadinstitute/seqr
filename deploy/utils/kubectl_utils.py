import logging
from deploy.utils.constants import DEPLOYABLE_COMPONENTS
from seqr.utils.shell_utils import try_running_shell_command, run_shell_command_async

logger = logging.getLogger(__name__)



def _get_resource_info(
        resource_type="pod",
        labels={},
        json_path=".items[0].metadata.name",
        errors_to_ignore=("array index out of bounds: index 0",),
        verbose=False,
    ):
    """Runs 'kubectl get <resource_type>' command to retrieve info about this resource.

    Args:
        component (string): keyword to use for looking up a kubernetes entity (eg. 'phenotips' or 'nginx')
        labels (dict): (eg. {'name': 'phenotips'})
        json_path (string): a json path query string (eg. ".items[0].metadata.name")
        errors_to_ignore (list):
        verbose (bool):
    Returns:
        (string) resource value (eg. "postgres-410765475-1vtkn")
    """

    l_arg = ",".join(["%s=%s" % (key, value) for key, value in labels.items()])

    output = try_running_shell_command(
        "kubectl get %(resource_type)s -l %(l_arg)s -o jsonpath={%(json_path)s}" % locals(),
        errors_to_ignore=errors_to_ignore,
        verbose=verbose,
    )

    return output.strip('\n') if output is not None else None


POD_READY_STATUS = "IS_READY"
POD_RUNNING_STATUS = "IS_RUNNING"
def get_pod_status(pod_name, deployment_label=None, print_status=True, status_type=POD_RUNNING_STATUS):
    labels = {"name": pod_name}
    if deployment_label:
        labels["deployment"] = deployment_label

    if status_type == POD_READY_STATUS:
        json_path = ".items[0].status.containerStatuses[0].ready"
    elif status_type == POD_RUNNING_STATUS:
        json_path = ".items[0].status.phase"
    else:
        raise ValueError("Unexpected status_type arg: %s" % str(status_type))

    result = _get_resource_info(
        labels = labels,
        resource_type="pod",
        json_path=json_path,
        errors_to_ignore=["array index out of bounds: index 0"],
        verbose=False,
    )

    if print_status:
        logger.info("Status: " + str(result))

    return result

def get_pod_name(pod_name, deployment_label=None):
    labels = {"name": pod_name}
    if deployment_label:
        labels["deployment"] = deployment_label

    return _get_resource_info(
        labels=labels,
        resource_type="pod",
        json_path=".items[0].metadata.name",
        errors_to_ignore=["array index out of bounds: index 0"],
        verbose=False,
    )


def get_service_name(service_name, deployment_label=None):
    labels = {"name": service_name}
    if deployment_label:
        labels["deployment"] = deployment_label

    return _get_resource_info(
        labels=labels,
        resource_type="pod",
        json_path=".items[0].metadata.name",
        errors_to_ignore=["array index out of bounds: index 0"],
        verbose=False,
    )


def get_node_name():
    return _get_resource_info(
        resource_type="nodes",
        json_path=".items[0].metadata.name",
        errors_to_ignore=["array index out of bounds: index 0"],
        verbose=False,
    )


def try_running_shell_command_in_pod(pod_name, command, deployment_label=None, errors_to_ignore=None, verbose=False, is_interactive=False):
    """Runs a kubernetes command to execute an arbitrary linux command string on the given pod.

    Args:
        pod_name (string): keyword to use for looking up a kubernetes pod (eg. 'phenotips' or 'nginx')
        command (string): the command to execute.
        is_interactive (bool): whether the command expects input from the user
    """

    if pod_name in DEPLOYABLE_COMPONENTS:
        full_pod_name = get_pod_name(pod_name, deployment_label=deployment_label)
        if not full_pod_name:
            raise ValueError("No '%(pod_name)s' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())
    else:
        full_pod_name = pod_name

    it_arg = "-it" if is_interactive else ""
    try_running_shell_command("kubectl exec %(it_arg)s %(full_pod_name)s -- %(command)s" % locals(), errors_to_ignore=errors_to_ignore, verbose=verbose, is_interactive=is_interactive)
