import glob
import logging
import os
import shutil
import time

from seqr.utils.shell_utils import run_shell_command
from settings import BASE_DIR
from deploy.kubernetes.utils.constants import DEPLOYMENT_SCRIPTS
from deploy.kubernetes.utils.servctl_utils import render, script_processor, template_processor, \
    check_kubernetes_context, retrieve_settings

logger = logging.getLogger(__name__)


def deploy(deployment_label, component=None, output_dir=None, other_settings={}):
    """
    Args:
        deployment_label (string): one of the DEPLOYMENT_LABELS  (eg. "local", or "gcloud")
        component (string): optionally specifies one of the components from the DEPLOYABLE_COMPONENTS lists (eg. "postgres" or "phenotips").
            If this is set to None, all DEPLOYABLE_COMPONENTS will be deployed in sequence.
        output_dir (string): path of directory where to put deployment logs and rendered config files
        other_settings (dict): a dictionary of other key-value pairs for use during deployment
    """

    check_kubernetes_context(deployment_label)

    # parse settings files
    settings = retrieve_settings(deployment_label)
    settings.update(other_settings)

    # configure deployment dir
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    output_dir = os.path.join(settings["DEPLOYMENT_TEMP_DIR"], "seqr_deployments/%(timestamp)s_%(deployment_label)s" % locals())

    # configure logging output
    log_dir = os.path.join(output_dir, "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    log_file_path = os.path.join(log_dir, "deploy.log")
    sh = logging.StreamHandler(open(log_file_path, "w"))
    sh.setLevel(logging.INFO)
    logger.addHandler(sh)
    logger.info("Starting log file: %(log_file_path)s" % locals())

    # normalize settings
    for key, value in settings.items():
        key = key.upper()
        settings[key] = value
        logger.info("%s = %s" % (key, value))

    # copy settings, templates and scripts to output directory
    for file_path in glob.glob("deploy/kubernetes/templates/*/*.*") + glob.glob("deploy/kubernetes/templates/*/*/*.*"):
        file_path = file_path.replace('deploy/kubernetes/templates/', '')
        input_base_dir = os.path.join(BASE_DIR, 'deploy/kubernetes/templates')
        output_base_dir = os.path.join(output_dir, 'deploy/kubernetes/configs')
        render(template_processor, input_base_dir, file_path, settings, output_base_dir)

    for file_path in glob.glob(os.path.join("deploy/kubernetes/scripts/*.sh")):
        render(script_processor, BASE_DIR, file_path, settings, output_dir)

    #for file_path in glob.glob(os.path.join("deploy/kubernetes/scripts/*.py")):
    #    shutil.copy(file_path, os.path.join(output_dir, 'kubernetes/scripts', os.path.basename(file_path)))

    for file_path in glob.glob(os.path.join("deploy/kubernetes/settings/*.yaml")):
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
    secrets_src_dir = os.path.join(BASE_DIR, "deploy/kubernetes/secrets/%(deployment_label)s" % locals())
    secrets_dest_dir = os.path.join(output_dir, "deploy/kubernetes/secrets/%(deployment_label)s" % locals())
    logger.info("Copying %(secrets_src_dir)s to %(secrets_dest_dir)s" % locals())
    shutil.copytree(secrets_src_dir, secrets_dest_dir)

    # write out ConfigMap file so that settings key/values can be added as environment variables in each of the pods
    with open(os.path.join(output_dir, "deploy/kubernetes/settings/all-settings.properties"), "w") as f:
        for key, value in settings.items():
            f.write("%s=%s\n" % (key, value))

    # deploy
    if component:
        deployment_scripts = [s for s in DEPLOYMENT_SCRIPTS if 'deploy_begin' in s or component in s or component.replace('-', '_') in s]
    else:
        deployment_scripts = DEPLOYMENT_SCRIPTS

    os.chdir(os.path.join(output_dir, "deploy"))
    logger.info("Switched to %(output_dir)s" % locals())

    for path in deployment_scripts:
        logger.info("=========================")
        run_shell_command(path, verbose=True).wait()
