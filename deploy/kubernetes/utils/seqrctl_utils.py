import collections
import jinja2
import logging
import os
import subprocess
import yaml

logger = logging.getLogger()


def parse_settings(config_file_paths):
    """Reads and parses the yaml settings file(s) for the given label, and returns a dict of parsed
    settings.
    """

    all_settings = collections.OrderedDict()
    for config_path in config_file_paths:
        with open(config_path) as f:
            try:
                config_settings = yaml.load(f)
            except yaml.parser.ParserError as e:
                raise ValueError('unable to parse yaml file %(config_path)s: %(e)s' % locals())

            if not config_settings:
                raise ValueError('yaml file %(config_path)s appears to be empty' % locals())

            logger.info("Parsed %3d settings from %s" % (len(config_settings), config_path))

            all_settings.update(config_settings)

    return all_settings


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


def run_deployment_scripts(script_paths, working_directory):
    """Switches current directory to working_directory and executes the given list of shell scripts.

    Args:
        script_paths (list): list of executable shell script paths to execute in series. Any
            relative paths are assumed to be relative to the working_directory.
        working_directory (string): directory from which to run these shell commands
    """

    os.chdir(working_directory)
    logger.info("Switched to %(working_directory)s" % locals())

    for path in script_paths:
        logger.info("=========================")
        logger.info("Running %(path)s" % locals())
        os.system(path)


def _get_pod_name(resource):
    """Runs 'kubectl get pods | grep <resource>' command to retrieve the full pod name.

    Args:
        resource (string): keyword to use for looking up a kubernetes pod (eg. 'phenotips' or 'nginx')
    Returns:
        (string) full pod name
    """
    output = subprocess.check_output("kubectl get pods -o=name | grep '%(resource)s-' | cut -f 2 -d /" % locals(), shell=True)
    return output.strip('\n')


def _run_shell_command(command):
    """Runs the given command in a shell.

    Return:
        subprocess pid object
    """

    logger.info("Running: '%s'" % command)

    p = subprocess.Popen(command, shell=True)
    return p


def print_log(resources, enable_stream_log):
    """Executes kubernetes command to print the log for the given pod.

    Args:
        resources (list): one or more keywords to use for looking up a kubernetes pods (eg. 'phenotips' or 'nginx').
            If more than one is specified, logs will be printed from each resource in parallel.
        enable_stream_log (bool): whether to continuously stream the log instead of just printing
            the log up to now.
    """
    stream_arg = "-f" if enable_stream_log else ""

    ps = []
    for resource in resources:
        pod_name = _get_pod_name(resource)

        p = _run_shell_command("kubectl logs %(stream_arg)s %(pod_name)s" % locals())
        ps.append(p)

    for p in ps:
        p.wait()


def exec_command(resource, command):
    """Runs a kubernetes command to execute an arbitrary linux command string on the given pod.

    Args:
        resource (string): keyword to use for looking up a kubernetes pod (eg. 'phenotips' or 'nginx')
        command (string): the command to execute.
    """

    pod_name = _get_pod_name(resource)

    _run_shell_command("kubectl exec -it %(pod_name)s %(command)s" % locals()).wait()


def port_forward(resource_port_pairs=[]):
    """Executes kubernetes command to forward traffic on the given localhost port to the given pod.
    While this is running, connecting to localhost:<port> will be the same as connecting to that port
    from the pod's internal network.

    Args:
        resource_port_pairs (list): 2-tuple(s) containing keyword to use for looking up a kubernetes
            pod, along with the port to forward to that pod (eg. ('mongo', 27017), or ('phenotips', 8080)),

    """
    ps = []
    for resource, port in resource_port_pairs:
        pod_name = _get_pod_name(resource)
        logger.info("Forwarding port %s for %s" % (port, resource))
        p = subprocess.Popen("kubectl port-forward %(pod_name)s %(port)s" % locals(), shell=True)
        ps.append(p)

    for p in ps:
        p.wait()


def create_user():
    """Creates a seqr super user"""

    pod_name = _get_pod_name('seqr')

    _run_shell_command("kubectl exec -it %(pod_name)s -- python -u manage.py createsuperuser" % locals()).wait()
    #--noinput --username $USER --email $EMAIL


def load_example_project():
    """Load example project"""

    pod_name = _get_pod_name('seqr')

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
