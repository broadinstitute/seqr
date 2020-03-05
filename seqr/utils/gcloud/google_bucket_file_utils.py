import logging
import subprocess

from seqr.utils.shell_utils import run

logger = logging.getLogger(__name__)


def _gsutil_command(command, gs_path):
    #  Anvil buckets are requester-pays and we bill them to the anvil project
    project_arg = '-u anvil-datastorage ' if gs_path.startswith('gs://fc-secure') else ''
    return 'gsutil {project_arg}{command} {gs_path}'.format(
        project_arg=project_arg, command=command, gs_path=gs_path,
    )


def is_google_bucket_file_path(file_path):
    return file_path.startswith("gs://")


def does_google_bucket_file_exist(gs_path):
    try:
        run(_gsutil_command('ls', gs_path), verbose=False)
        return True
    except RuntimeError:
        return False


def google_bucket_file_iter(gs_path, byte_range=None):
    """Iterate over lines in the given file"""
    range_arg = ' -r {}-{}'.format(byte_range[0], byte_range[1]) if byte_range else ''
    command = _gsutil_command('cat{}'.format(range_arg), gs_path)
    if gs_path.endswith("gz"):
        command += "| gunzip -c -q - "
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    for line in process.stdout:
        yield line
