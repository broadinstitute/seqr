import collections
import glob
import logging
import os
import shutil
import subprocess
import sys
import time

from utils.constants import BASE_DIR
from utils.seqrctl_utils import load_settings, render, script_processor, template_processor, _run_shell_command

logger = logging.getLogger()


def deploy(deployment_label, force, component=None, output_dir=None, other_settings={}):
    """
    Args:
        deployment_label (string): one of the DEPLOYMENT_LABELS  (eg. "local", or "gcloud")
        force (bool): whether to redo some parts of the deployment from scratch
        component (string): one of the components from DEPLOYABLE_COMPONENTS (eg. "postgres" or "phenotips")
        output_dir (string): path of directory where to put deployment logs and rendered config files
        other_settings (dict): a dictionary of other key-value pairs for use during deployment
    """

    # make sure the environment is configured to use a local kube-solo cluster, and not gcloud or something else
    cmd = 'kubectl config current-context'
    kubectl_current_context = subprocess.check_output(cmd, shell=True).strip()
    if deployment_label == "local":
        if kubectl_current_context != 'kube-solo':
            logger.error("%(cmd)s returned '%(kubectl_current_context)s'. For %(deployment_label)s deployment, this is "
                         "expected to equal 'kube-solo'. Please configure your shell environment "
                         "to point to a local kube-solo cluster by installing "
                         "kube-solo from https://github.com/TheNewNormal/kube-solo-osx, starting the kube-solo VM, "
                         "and then clicking on 'Preset OS Shell' in the kube-solo menu to launch a pre-configured shell." % locals())
            sys.exit(-1)

    elif deployment_label == "gcloud":
        if not kubectl_current_context.startswith('gke_'):
            logger.error("%(cmd)s returned '%(kubectl_current_context)s'. For %(deployment_label)s deployment, this is "
                         "expected to start with 'gke_'. Please configure your shell environment "
                         "to point to a gcloud cluster by running "
                         "gcloud ??? and re-running " % locals())
            sys.exit(-1)
    else:
        raise ValueError("Unexpected value for deployment_label: %s" % deployment_label)

    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    output_dir = output_dir or "deployments/%(timestamp)s_%(deployment_label)s" % locals()

    # configure logging output
    log_dir = os.path.join(output_dir, "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    log_file_path = os.path.join(log_dir, "deploy.log")
    sh = logging.StreamHandler(open(log_file_path, "w"))
    sh.setLevel(logging.INFO)
    logger.addHandler(sh)
    logger.info("Starting log file: %(log_file_path)s" % locals())

    # parse config files
    settings = collections.OrderedDict()

    settings['STARTED_VIA_SEQRCTL'] = True
    settings['HOME'] = os.path.expanduser("~")
    settings['SEQR_REPO_PATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))

    load_settings([
        os.path.join(BASE_DIR, "config/shared-settings.yaml"),
        os.path.join(BASE_DIR, "config/%(deployment_label)s-settings.yaml" % locals())
    ], settings)

    settings.update(other_settings)

    for key, value in settings.items():
        key = key.upper()
        settings[key] = value
        logger.info("%s = %s" % (key, value))

    # copy configs, templates and scripts to output directory
    output_base_dir = os.path.join(output_dir, 'configs')
    for file_path in glob.glob("templates/*/*.*") + glob.glob("templates/*/*/*.*"):
        file_path = file_path.replace('templates/', '')
        input_base_dir = os.path.join(BASE_DIR, 'templates')
        render(template_processor, input_base_dir, file_path, settings, output_base_dir)

    for file_path in glob.glob(os.path.join("scripts/*.sh")):
        render(script_processor, BASE_DIR, file_path, settings, output_dir)

    for file_path in glob.glob(os.path.join("config/*.yaml")):
        shutil.copy(file_path, output_base_dir)

    # copy docker directory to output directory
    docker_src_dir = os.path.join(BASE_DIR, "../docker/")
    docker_dest_dir = os.path.join(output_dir, "docker")
    logger.info("Copying %(docker_src_dir)s to %(docker_dest_dir)s" % locals())
    shutil.copytree(docker_src_dir, docker_dest_dir)

    # copy secrets directory
    secrets_src_dir = os.path.join(BASE_DIR, "secrets/%(deployment_label)s" % locals())
    secrets_dest_dir = os.path.join(output_dir, "secrets/%(deployment_label)s" % locals())
    logger.info("Copying %(secrets_src_dir)s to %(secrets_dest_dir)s" % locals())
    shutil.copytree(secrets_src_dir, secrets_dest_dir)

    # deploy
    os.environ['FORCE'] = "true" if force else ''

    deployment_scripts = [
        'scripts/deploy_init.sh',
        'scripts/deploy_nginx.sh',
        'scripts/deploy_postgres.sh',
        'scripts/deploy_mongo.sh',
        'scripts/deploy_phenotips.sh',
        'scripts/deploy_matchbox.sh',
        'scripts/deploy_seqr.sh',
    ]

    if component:
        deployment_scripts = [s for s in deployment_scripts if 'init' in s or component in s]

    os.chdir(output_dir)
    logger.info("Switched to %(output_dir)s" % locals())

    for path in deployment_scripts:
        logger.info("=========================")
        _run_shell_command(path, verbose=True).wait()
