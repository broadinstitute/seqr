import logging
import time

from deploy.servctl_utils.kubectl_utils import is_pod_running, wait_for_resource, get_resource_name
from deploy.servctl_utils.yaml_settings_utils import load_settings
from deploy.servctl_utils.shell_utils import run

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def delete_component(component, deployment_target=None):
    """Runs kubectl commands to delete any running deployment, service, or pod objects for the given component(s).

    Args:
        component (string): component to delete (eg. 'postgres' or 'nginx').
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"
    """
    pod_name = run(
        'deploy/kubectl_helpers/utils/get_pod_name.sh {} {}'.format(deployment_target.replace('gcloud-', ''), component))

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
    elif component == 'postgres':
        run('gcloud sql instances delete postgres-{}'.format(deployment_target.replace('gcloud-', '')))
    elif component == "nginx":
        raise ValueError("TODO: implement deleting nginx")

    run("kubectl delete deployments %(component)s" % locals(), errors_to_ignore=["not found"])
    run("kubectl delete services %(component)s" % locals(), errors_to_ignore=["not found"])

    if pod_name:
        run("kubectl delete pods %(pod_name)s" % locals(), errors_to_ignore=["not found"])

        logger.info("waiting for \"%s\" to exit Running status" % component)
        while is_pod_running(component, deployment_target):
            time.sleep(5)


    # print services and pods status
    run("kubectl get services" % locals(), verbose=True)
    run("kubectl get pods" % locals(), verbose=True)


def delete_all(deployment_target):
    """Runs kubectl and gcloud commands to delete the given cluster and all objects in it.

    Args:
        deployment_target (string): value from DEPLOYMENT_TARGETS - eg. "gcloud-dev"

    """
    run('deploy/kubectl_helpers/utils/check_context.sh {}'.format(deployment_target.replace('gcloud-', '')))
    settings = {}

    load_settings([
        "deploy/kubernetes/shared-settings.yaml",
        "deploy/kubernetes/%(deployment_target)s-settings.yaml" % locals(),
    ], settings)

    run("gcloud container clusters delete --project %(GCLOUD_PROJECT)s --zone %(GCLOUD_ZONE)s --no-async %(CLUSTER_NAME)s" % settings, is_interactive=True)
    run('gcloud sql instances delete postgres-{}'.format(deployment_target.replace('gcloud-', '')))

    for disk_label in [d.strip() for d in settings['DISKS'].split(',') if d]:
        for disk_name in  get_disk_names(disk_label, settings):
            run('gcloud compute disks delete --zone {zone} {disk_name}'.format(
                zone=settings['GCLOUD_ZONE'], disk_name=disk_name), is_interactive=True)


def get_disk_names(disk, settings):
    num_disks = settings.get('{}_NUM_DISKS'.format(disk.upper().replace('-', '_'))) or 1
    return [
        '{cluster_name}-{disk}-disk{suffix}'.format(
            cluster_name=settings['CLUSTER_NAME'], disk=disk, suffix='-{}'.format(i + 1) if num_disks > 1 else '')
    for i in range(num_disks)]

