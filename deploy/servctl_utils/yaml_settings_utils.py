import collections
import io
import jinja2
import logging
import os
import socket
import time
import yaml


logger = logging.getLogger()


def _get_ip_address():
    """Returns the localhost ip address as a string (eg. "192.168.0.6")."""

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def _parse_jinja_template(jinja_template_path, template_variables):
    with io.open(jinja_template_path, encoding="UTF-8") as jinja_template_file:
        try:
            jinja_template_contents = jinja_template_file.read()
            yaml_string = jinja2.Template(jinja_template_contents).render(template_variables)
        except TypeError as e:
            raise ValueError('unable to render file: %(e)s' % locals())

    return yaml_string


def load_settings(settings_file_paths, settings=None):
    """Parses yaml settings file(s) and returns a dictionary of settings.
    These yaml files are treated as Jinja templates.
    If a settings dictionary is also provided as an argument, it will be used as context for Jinja template processing.

    Args:
        settings_file_paths (list): a list of yaml settings file paths to load
        settings (dict): optional dictionary of settings values

    Return:
        dict: settings file containing all settings parsed from the given settings file(s)
    """

    if settings is None:
        settings = collections.OrderedDict()

    # add generic global options
    settings["HOME"] = os.path.expanduser("~")
    settings["TIMESTAMP"] = time.strftime("%Y%m%d_%H%M%S")
    settings["HOST_MACHINE_IP"] = _get_ip_address()

    # process settings_file_paths
    for settings_path in settings_file_paths:
        yaml_string = _parse_jinja_template(settings_path, template_variables=settings)

        try:
            settings_from_this_file = yaml.load(yaml_string)
        except yaml.parser.ParserError as e:
            raise ValueError('Unable to parse yaml file %(settings_path)s: %(e)s' % locals())

        if not settings_from_this_file:
            raise ValueError('yaml file %(settings_path)s appears to be empty' % locals())

        logger.info("Parsed %3d settings from %s" % (len(settings_from_this_file), settings_path))

        settings.update(settings_from_this_file)

    return settings


def process_jinja_template(input_base_dir, relative_file_path, template_variables, output_base_dir):
    """Reads a Jinja template from the given input file path, applies template_variables, and writes the result to
    {output_base_dir}/{relative_file_path}.

    Args:
        input_base_dir (string): The base directory for input file paths.
        relative_file_path (string): template file path relative to base_dir
        template_variables (dict): dictionary of key-value pairs for resolving any variables in the Jinja template
        output_base_dir (string): The rendered jinja template will be written to {output_base_dir}/{relative_file_path}
    """

    # read in {input_base_dir}/{relative_file_path file}
    yaml_string = _parse_jinja_template(
        os.path.join(input_base_dir, relative_file_path),
        template_variables=template_variables)

    logger.info("Parsed %s" % relative_file_path)

    # write out yaml_string to {output_base_dir}/{relative_file_path file}
    output_file_path = os.path.join(output_base_dir, relative_file_path)
    output_dir_path = os.path.dirname(output_file_path)

    if not os.path.isdir(output_dir_path):
        os.makedirs(output_dir_path)

    try:
        with open(output_file_path, 'w') as ostream:
            ostream.write(yaml_string)
    except Exception as e:
        logger.error("Couldn't write out %s" % relative_file_path)
        raise

    #os.chmod(output_file_path, 0x777)
    logger.info("-- wrote out %s" % output_file_path)

