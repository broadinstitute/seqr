import base64
import collections

import jinja2
import logging
import os
import subprocess
import sys
import time
import yaml

from utils.constants import BASE_DIR, PORTS, COMPONENTS_TO_OPEN_IN_BROWSER
from seqr.utils.shell_utils import run_shell_command, wait_for

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
        components = list(PORTS.keys())

    return [(component, port) for component in components for port in PORTS[component]]


def load_settings(config_file_paths, settings=None, secrets=False):
    """Reads and parses the yaml settings file(s) and returns a dictionary of settings.
    These yaml files are treated as jinja templates. If a settings dictionary is also provided
    as an argument, it will be used as context for jinja template processing.

    Args:
        config_file_paths (list): a list of yaml settings file paths to load
        settings (dict): optional dictionary of settings files
        secrets (bool): if False, the settings files are assumed to be yaml key-value pairs.
            if True, the files are parsed as Kubernetes Secrets files with base64-encoded values
    Return:
        dict: settings file containing all settings parsed from the given settings file
    """

    if settings is None:
        settings = collections.OrderedDict()

    for config_path in config_file_paths:
        with open(config_path) as f:
            try:
                yaml_string = template_processor(f, settings)
            except TypeError as e:
                raise ValueError('unable to render file %(file_path)s: %(e)s' % locals())

            try:
                config_settings = yaml.load(yaml_string)
            except yaml.parser.ParserError as e:
                raise ValueError('unable to parse yaml file %(config_path)s: %(e)s' % locals())

            if not config_settings:
                raise ValueError('yaml file %(config_path)s appears to be empty' % locals())

            if secrets:
                config_settings = config_settings['data']
                import pprint
                pprint.pprint(config_settings)
                for key, value in config_settings.items():
                    config_settings[key] = base64.b64decode(value)

            logger.info("Parsed %3d settings from %s" % (len(config_settings), config_path))

            settings.update(config_settings)

    return settings


def script_processor(bash_script_istream, settings):
    """Returns a string representation of the given bash script such that environment variables are
    bound to their values in settings.

    Args:
        bash_script_istream (iter): a stream or iterator over lines in the bash script
        settings (dict): a dictionary of keys & values to add to the environment of the given bash script at runtime
    Returns:
        string: the same bash script with variables resolved to values in the settings dict.
    """
    result = ""
    for i, line in enumerate(bash_script_istream):
        is_shebang_line = (i == 0 and line.startswith('#!'))
        if is_shebang_line:
            result += line  # write shebang line before settings

        if i == 0:
            # insert a line that sets a bash environment variable for each key-value pair in setting
            result += '\n'
            for key, value in settings.items():
                if type(value) == str:
                    if "'" in value:
                        # NOTE: single quotes in settings values will break the naive approach to settings used here.
                        raise ValueError("%(key)s=%(value)s value contains unsupported single-quote char" % locals())

                    value = "'%s'" % value  # put quotes around the string in case it contains spaces
                elif type(value) == bool:
                    value = str(value).lower()

                result += "%(key)s=%(value)s\n" % locals()

            result += '\n'

        if not is_shebang_line:
            result += line  # write all other lines after settings

    return result


def template_processor(template_istream, settings):
    """Returns a string representation of the given jinja template rendered using the key & values
    from the settings dict.

    Args:
        template_istream (iter): a stream or iterator over lines in the jinja template
        settings (dict): keys & values to use when rendering the template
    Returns:
        string: the same template with variables resolved to values in the settings dict.
    """

    template_contents = ''.join(template_istream)
    return jinja2.Template(template_contents).render(settings)


def render(render_func, input_base_dir, relative_file_path, settings, output_base_dir):
    """Calls the given render_func to convert the input file + settings dict to a rendered in-memory
    config which it then writes out to the output directory.

    Args:
        render_func: A function that takes 2 arguments -
            1) an input stream that reads from a config template
            2) a settings dict for resolving variables in the config template
            It then returns the rendered string representation of the config, with the settings applied.
        input_base_dir (string): The base directory for input file paths.
        relative_file_path (string): Config template file path relative to base_dir
        settings (dict): dictionary of key-value pairs for resolving any variables in the config template
        output_base_dir (string): The rendered config will be written to the file  {output_base_dir}/{relative_file_path}
    """

    input_file_path = os.path.join(input_base_dir, relative_file_path)
    with open(input_file_path) as istream:
        try:
            rendered_string = render_func(istream, settings)
        except TypeError as e:
            raise ValueError('unable to render file %(file_path)s: %(e)s' % locals())

    logger.info("Parsed %s" % relative_file_path)

    output_file_path = os.path.join(output_base_dir, relative_file_path)
    output_dir_path = os.path.dirname(output_file_path)

    if not os.path.isdir(output_dir_path):
        os.makedirs(output_dir_path)

    with open(output_file_path, 'w') as ostream:
        ostream.write(rendered_string)
    os.chmod(output_file_path, 0x777)
    logger.info("-- wrote rendered output to %s" % output_file_path)


def _get_resource_name(component, resource_type="pod"):
    """Runs 'kubectl get <resource_type> | grep <component>' command to retrieve the full name of this resource.

    Args:
        component (string): keyword to use for looking up a kubernetes entity (eg. 'phenotips' or 'nginx')
    Returns:
        (string) full resource name (eg. "postgres-410765475-1vtkn")
    """

    output = subprocess.check_output("kubectl get %(resource_type)s -l name=%(component)s -o jsonpath={.items[0].metadata.name}" % locals(), shell=True)
    output = output.strip('\n')

    return output


def _get_pod_name(component):
    """Runs 'kubectl get pods | grep <component>' command to retrieve the full pod name.

    Args:
        component (string): keyword to use for looking up a kubernetes pod (eg. 'phenotips' or 'nginx')
    Returns:
        (string) full pod name (eg. "postgres-410765475-1vtkn")
    """
    return _get_resource_name(component, resource_type="pod")


def retrieve_settings(deployment_label):
    settings = collections.OrderedDict()

    settings['STARTED_VIA_SEQRCTL'] = True
    settings['TIMESTAMP'] = time.strftime("%Y%m%d_%H%M%S")
    settings['HOME'] = os.path.expanduser("~")
    settings['SEQR_REPO_PATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))

    load_settings([
        os.path.join(BASE_DIR, "config/shared-settings.yaml"),
        os.path.join(BASE_DIR, "config/%(deployment_label)s-settings.yaml" % locals())
    ], settings)

    return settings



def check_kubernetes_context(deployment_label):
    # make sure the environment is configured to use a local kube-solo cluster, and not gcloud or something else
    try:
        cmd = 'kubectl config current-context'
        kubectl_current_context = subprocess.check_output(cmd, shell=True).strip()
    except subprocess.CalledProcessError as e:
        logger.error('Error while running "kubectl config current-context": %s', e)
        #i = raw_input("Continue? [Y/n] ")
        #if i != 'Y' and i != 'y':
        #    sys.exit('Exiting...')
        return

    if deployment_label == "local":
        if kubectl_current_context != 'kube-solo':
            logger.error(("'%(cmd)s' returned '%(kubectl_current_context)s'. For %(deployment_label)s deployment, this is "
                          "expected to equal 'kube-solo'. Please configure your shell environment "
                          "to point to a local kube-solo cluster by installing "
                          "kube-solo from https://github.com/TheNewNormal/kube-solo-osx, starting the kube-solo VM, "
                          "and then clicking on 'Preset OS Shell' in the kube-solo menu to launch a pre-configured shell.") % locals())
            sys.exit(-1)

    elif deployment_label.startswith("gcloud"):
        suffix = deployment_label.split("-")[-1]  # "dev" or "prod"
        if not kubectl_current_context.startswith('gke_') or not kubectl_current_context.endswith(suffix):
            logger.error(("'%(cmd)s' returned '%(kubectl_current_context)s' which doesn't match %(deployment_label)s. "
                          "To fix this, run:\n\n   "
                          "gcloud container clusters get-credentials <cluster-name>\n\n"
                          "Using one of these clusters: " + subprocess.check_output("gcloud container clusters list", shell=True) +
                          "\n\n") % locals())
            sys.exit(-1)
    else:
        raise ValueError("Unexpected value for deployment_label: %s" % deployment_label)


def set_environment(deployment_label):
    settings = retrieve_settings(deployment_label)
    run_shell_command("gcloud config set project %(CLUSTER_NAME)s" % settings)
    run_shell_command("gcloud container clusters get-credentials %(CLUSTER_NAME)s --zone=%(GCLOUD_ZONE)s" % settings)


def lookup_json_path(resource_type="pod", labels={}, json_path=".items[0].metadata.name"):
    """Runs 'kubectl get <resource_type> | grep <component>' command to retrieve the full name of this resource.

    Args:
        component (string): keyword to use for looking up a kubernetes entity (eg. 'phenotips' or 'nginx')
        labels (dict):
        json_path (string):
    Returns:
        (string) resource value (eg. "postgres-410765475-1vtkn")
    """

    l_args = " ".join(['-l %s=%s' % (key, value) for key, value in labels.items()])
    output = subprocess.check_output("kubectl get %(resource_type)s %(l_args)s -o jsonpath={%(json_path)s}" % locals(), shell=True)
    output = output.strip('\n')

    return output


def show_status():
    """Print status of various docker and kubernetes subsystems"""

    run_shell_command("docker info").wait()
    run_shell_command("docker images").wait()
    run_shell_command("kubectl cluster-info").wait()
    run_shell_command("kubectl config view | grep 'username\|password'").wait()
    run_shell_command("kubectl get services").wait()
    run_shell_command("kubectl get pods").wait()
    run_shell_command("kubectl config current-context").wait()


def show_dashboard():
    """Launches the kubernetes dashboard"""

    proxy = run_shell_command('kubectl proxy')
    run_shell_command('open http://localhost:8001/ui')
    proxy.wait()


def print_log(components, enable_stream_log, wait=True):
    """Executes kubernetes command to print the log for the given pod.

    Args:
        components (list): one or more keywords to use for looking up a kubernetes pods (eg. 'phenotips' or 'nginx').
            If more than one is specified, logs will be printed from each component in parallel.
        enable_stream_log (bool): whether to continuously stream the log instead of just printing
            the log up to now.
        wait (bool): Whether to block indefinitely as long as the forwarding process is running.

    Returns:
        (list): Popen process objects for the kubectl port-forward processes.
    """
    stream_arg = "-f" if enable_stream_log else ""

    procs = []
    for component in components:
        pod_name = _get_pod_name(component)
        if not pod_name:
            raise ValueError("No '%(component)s' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

        p = run_shell_command("kubectl logs %(stream_arg)s %(pod_name)s" % locals())
        procs.append(p)

    if wait:
        wait_for(procs)

    return procs


def exec_command(component, command, is_interactive=False):
    """Runs a kubernetes command to execute an arbitrary linux command string on the given pod.

    Args:
        component (string): keyword to use for looking up a kubernetes pod (eg. 'phenotips' or 'nginx')
        command (string): the command to execute.
        is_interactive (bool): whether the command expects input from the user
    """

    pod_name = _get_pod_name(component)
    if not pod_name:
        raise ValueError("No '%(component)s' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    it_flag = '-it' if is_interactive else ''
    run_shell_command("kubectl exec %(it_flag)s %(pod_name)s %(command)s" % locals(), is_interactive=is_interactive).wait()


def port_forward(component_port_pairs=[], wait=True, open_browser=False):
    """Executes kubernetes command to forward traffic on the given localhost port to the given pod.
    While this is running, connecting to localhost:<port> will be the same as connecting to that port
    from the pod's internal network.

    Args:
        component_port_pairs (list): 2-tuple(s) containing keyword to use for looking up a kubernetes
            pod, along with the port to forward to that pod (eg. ('mongo', 27017), or ('phenotips', 8080))
        wait (bool): Whether to block indefinitely as long as the forwarding process is running.
        open_browser (bool): If component_port_pairs includes components that have an http server
            (eg. "seqr" or "phenotips"), then open a web browser window to the forwarded port.
    Returns:
        (list): Popen process objects for the kubectl port-forward processes.
    """
    procs = []
    for component, port in component_port_pairs:
        pod_name = _get_pod_name(component)
        if not pod_name:
            raise ValueError("No '%(component)s' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

        logger.info("Forwarding port %s for %s" % (port, component))
        p = run_shell_command("kubectl port-forward %(pod_name)s %(port)s" % locals())

        if open_browser and component in COMPONENTS_TO_OPEN_IN_BROWSER:
            os.system("open http://localhost:%s" % port)

        procs.append(p)

    if wait:
        wait_for(procs)

    return procs


def troubleshoot_component(component):
    """Executes kubernetes commands to print detailed debug output."""

    pod_name = _get_pod_name(component)

    run_shell_command("kubectl get pods -o yaml %(pod_name)s" % locals()).wait()


def kill_components(components=[]):
    """Executes kubernetes commands to kill deployments, services, pods for the given component(s)

    Args:
        components (list): one or more components to kill (eg. 'phenotips' or 'nginx').
    """
    for component in components:
        run_shell_command("kubectl delete deployments %(component)s" % locals()).wait()
        resource_name = _get_resource_name(component, resource_type='service')
        run_shell_command("kubectl delete services %(resource_name)s" % locals()).wait()
        resource_name = _get_pod_name(component)
        run_shell_command("kubectl delete pods %(resource_name)s" % locals()).wait()

        run_shell_command("kubectl get services" % locals()).wait()
        run_shell_command("kubectl get pods" % locals()).wait()


def reset_database(database=[]):
    """Executes kubernetes commands to delete and reset the given database.

    Args:
        component (list): one more keywords - "seqrdb", "phenotipsdb", "mongodb"
    """
    if "seqrdb" in database:
        postgres_pod_name = _get_pod_name('postgres')
        if not postgres_pod_name:
            logger.error("postgres pod must be running")
        else:
            run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'drop database seqrdb'" % locals()).wait()
            run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'create database seqrdb'" % locals()).wait()

    if "phenotipsdb" in database:
        postgres_pod_name = _get_pod_name('postgres')
        if not postgres_pod_name:
            logger.error("postgres pod must be running")
        else:
            run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'drop database xwiki'" % locals()).wait()
            run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'create database xwiki'" % locals()).wait()
            #run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres xwiki < data/init_phenotipsdb.sql" % locals()).wait()

    if "mongodb" in database:
        mongo_pod_name = _get_pod_name('mongo')
        if not mongo_pod_name:
            logger.error("mongo pod must be running")
        else:
            run_shell_command("kubectl exec %(mongo_pod_name)s -- mongo datastore --eval 'db.dropDatabase()'" % locals()).wait()


def kill_and_delete_all(deployment_label):
    """Execute kill and delete.

    Args:
        deployment_label (string): one of the DEPLOYMENT_LABELS  (eg. "local", or "gcloud")

    """
    settings = {}

    load_settings([
        os.path.join(BASE_DIR, "config/shared-settings.yaml"),
        os.path.join(BASE_DIR, "config/%(deployment_label)s-settings.yaml" % locals())
    ], settings)

    run_shell_command("scripts/delete_all.sh" % locals(), env=settings).wait()


def create_user():
    """Creates a seqr super user"""

    pod_name = _get_pod_name('seqr')
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    run_shell_command("kubectl exec -it %(pod_name)s -- python -u manage.py createsuperuser" % locals(), is_interactive=True).wait()


def delete_project(project_id):
    """Executes kubernetes commands to delete all data for the given project.

    Args:
        project_id (string): seqr project id
    """
    pod_name = _get_pod_name('seqr')
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py delete_project -f -i %(project_id)s" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py delete_phenotips_patients %(project_id)s" % locals()).wait()


