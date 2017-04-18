import base64
import collections
import jinja2
import logging
import os
import subprocess
import threading
import yaml

from utils.constants import PORTS, WEB_SERVER_COMPONENTS, BASE_DIR

logger = logging.getLogger()


def get_component_port_pairs(components=[]):
    """Uses the PORTS dictinoary to return a list of (<component name>, <port>) pairs (For example:
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


def show_status():
    """Print status of various docker and kubernetes subsystems"""

    _run_shell_command('docker info').wait()
    _run_shell_command('docker images').wait()
    _run_shell_command('kubectl cluster-info').wait()
    _run_shell_command('kubectl get services').wait()
    _run_shell_command('kubectl get pods').wait()
    _run_shell_command('kubectl config current-context').wait()


def show_dashboard():
    """Launches the kubernetes dashboard"""

    proxy = _run_shell_command('kubectl proxy')
    _run_shell_command('open http://localhost:8001/ui')
    proxy.wait()


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

    output = subprocess.check_output("kubectl get %(resource_type)s -o=name | grep '%(component)s' | cut -f 2 -d /" % locals(), shell=True)
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


class _LogPipe(threading.Thread):
    """Based on: https://codereview.stackexchange.com/questions/6567/redirecting-subprocesses-output-stdout-and-stderr-to-the-logging-module """

    def __init__(self, log_level=logging.INFO):
        """Thread that reads data from a pipe and forwards it to logging.log"""
        threading.Thread.__init__(self)

        self.log_level = log_level
        self.fd_read, self.fd_write = os.pipe()
        self.pipe_reader = os.fdopen(self.fd_read)

        self.start()

    def fileno(self):
        """Return the write file descriptor of the pipe"""

        return self.fd_write

    def run(self):
        """Run the thread, forwarding pipe data to logging"""

        for line in iter(self.pipe_reader.readline, ''):
            logging.log(self.log_level, line.strip('\n'))

        self.pipe_reader.close()

    def close(self):
        """Close the write end of the pipe."""
        os.close(self.fd_write)


def _run_shell_command(command, is_interactive=True, verbose=True, env={}):
    """Runs the given command in a shell.

    Args:
        command (string): the command to run
        is_interactive (bool): Whether this command expects interactive input from the user
        verbose (bool): whether to print command to log
        env (dict): A custom environment in which to run
    Return:
        subprocess Popen object
    """
    full_env = dict(os.environ)  # copy external environment
    full_env.update(env)

    full_env.update({ key: str(value) for key, value in full_env.items() })  # make sure all values are strings

    if verbose:
        with_env = ""  # ("with env: " + ", ".join("%s=%s" % (key, value) for key, value in full_env.items())) if full_env else ""
        logger.info("Running: '%(command)s' %(with_env)s" % locals())

    if not is_interactive:
        # pipe output to log
        stdout_pipe = _LogPipe(logging.INFO)
        p = subprocess.Popen(command, shell=True, stdout=stdout_pipe, stderr=subprocess.STDOUT, env=full_env)
        stdout_pipe.close()
    else:
        p = subprocess.Popen(command, shell=True, env=full_env)

    return p


def wait_for(procs):
    """Takes a list of subprocess.Popen objects and doesn't return until all these processes have completed"""

    for proc in procs:
        proc.wait()

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

        p = _run_shell_command("kubectl logs %(stream_arg)s %(pod_name)s" % locals())
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
    _run_shell_command("kubectl exec %(it_flag)s %(pod_name)s %(command)s" % locals(), is_interactive=is_interactive).wait()


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
        p = _run_shell_command("kubectl port-forward %(pod_name)s %(port)s" % locals())

        if open_browser and component in WEB_SERVER_COMPONENTS:
            os.system("open http://localhost:%s" % PORTS[component][0])

        procs.append(p)

    if wait:
        wait_for(procs)

    return procs


def kill_components(components=[]):
    """Executes kubernetes commands to kill deployments, services, pods for the given component(s)

    Args:
        components (list): one or more components to kill (eg. 'phenotips' or 'nginx').
    """
    for component in components:
        _run_shell_command("kubectl delete deployments %(component)s" % locals()).wait()
        resource_name = _get_resource_name(component, resource_type='svc')
        _run_shell_command("kubectl delete services %(resource_name)s" % locals()).wait()
        resource_name = _get_pod_name(component)
        _run_shell_command("kubectl delete pods %(resource_name)s" % locals()).wait()

        _run_shell_command("kubectl get services" % locals()).wait()
        _run_shell_command("kubectl get pods" % locals()).wait()


def delete_data(data=[]):
    """Executes kubernetes commands to delete all persistant data from the specified subsystems.

    Args:
        data (list): one more keywords - "seqrdb", "phenotipsdb", "mongodb"
    """
    if "seqrdb" in data:
        postgres_pod_name = _get_pod_name('postgres')
        if not postgres_pod_name:
            logger.error("postgres pod must be running")
        else:
            _run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'drop database seqrdb'" % locals()).wait()
            _run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'create database seqrdb'" % locals()).wait()

    if "phenotipsdb" in data:
        postgres_pod_name = _get_pod_name('postgres')
        if not postgres_pod_name:
            logger.error("postgres pod must be running")
        else:
            _run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'drop database xwiki'" % locals()).wait()
            _run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres postgres -c 'create database xwiki'" % locals()).wait()
            #_run_shell_command("kubectl exec %(postgres_pod_name)s -- psql -U postgres xwiki < data/init_phenotipsdb.sql" % locals()).wait()

    if "mongodb" in data:
        mongo_pod_name = _get_pod_name('mongo')
        if not mongo_pod_name:
            logger.error("mongo pod must be running")
        else:
            _run_shell_command("kubectl exec %(mongo_pod_name)s -- mongo datastore --eval 'db.dropDatabase()'" % locals()).wait()


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

    _run_shell_command("scripts/delete_all.sh" % locals(), env=settings).wait()


def create_user():
    """Creates a seqr super user"""

    pod_name = _get_pod_name('seqr')
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    _run_shell_command("kubectl exec -it %(pod_name)s -- python -u manage.py createsuperuser" % locals(), is_interactive=True).wait()


def load_example_project():
    """Load example project"""

    pod_name = _get_pod_name('seqr')
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    _run_shell_command("kubectl exec %(pod_name)s -- wget -N https://storage.googleapis.com/seqr-public/test-projects/1kg_exomes/1kg.vep.vcf.gz" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- wget -N https://storage.googleapis.com/seqr-public/test-projects/1kg_exomes/1kg.ped" % locals()).wait()

    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_project 1kg '1kg'" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_individuals_to_project 1kg --ped 1kg.ped" % locals()).wait()

    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_vcf_to_project 1kg 1kg.vep.vcf.gz" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_project_to_phenotips 1kg '1kg'" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_individuals_to_phenotips 1kg --ped 1kg.ped" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py generate_pedigree_images 1kg" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_default_tags 1kg" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py load_project 1kg" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py load_project_datastore 1kg" % locals()).wait()


def load_reference_data():
    """Load reference data"""

    pod_name = _get_pod_name('seqr')
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    _run_shell_command("kubectl exec %(pod_name)s -- mkdir -p /data/reference_data/" % locals())
    _run_shell_command("kubectl exec %(pod_name)s -- wget -N https://storage.googleapis.com/seqr-public/reference-data/seqr-resource-bundle.tar.gz -P /data/reference_data/" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- wget -N http://seqr.broadinstitute.org/static/bundle/ExAC.r0.3.sites.vep.popmax.clinvar.vcf.gz -P /data/reference_data/" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- wget -N http://seqr.broadinstitute.org/static/bundle/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5a.20130502.sites.decomposed.with_popmax.vcf.gz -P /data/reference_data/" % locals()).wait()

    _run_shell_command("kubectl exec %(pod_name)s -- tar -xzf /data/reference_data/seqr-resource-bundle.tar.gz --directory /data/reference_data/" % locals()).wait()
    _run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py load_resources" % locals()).wait()

    _run_shell_command("kubectl exec %(pod_name)s -- /usr/local/bin/restart_django_server.sh" % locals()).wait()
