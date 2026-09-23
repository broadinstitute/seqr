import os
import subprocess # nosec

from google.cloud import storage

from seqr.utils.logging_utils import SeqrLogger

logger = SeqrLogger(__name__)


def _parse_gs_path(gs_path):
    if not is_google_bucket_file_path(gs_path):
        raise Exception('A Google Storage path is expected.')
    bucket_name, blob_name = gs_path.replace('gs://', '', 1).split('/', 1)
    return bucket_name, blob_name


def _run_gsutil_command(command, gs_path, gunzip=False, user=None, pipe_errors=False, no_project=False, additional_args=''):
    if not is_google_bucket_file_path(gs_path):
        raise Exception('A Google Storage path is expected.')

    #  Anvil buckets are requester-pays and we bill them to the anvil project
    google_project = get_google_project(gs_path) if not no_project else None
    project_arg = '-u {} '.format(google_project) if google_project else ''
    command = f'gsutil {project_arg}{command} {gs_path}{additional_args}'
    if gunzip:
        command += " | gunzip -c -q - "

    logger.info('==> {}'.format(command), user)
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE if pipe_errors else subprocess.STDOUT, shell=True) # nosec


def is_google_bucket_file_path(file_path):
    return file_path.startswith("gs://")


def get_google_project(gs_path):
    return 'anvil-datastorage' if gs_path.startswith('gs://fc-secure') else None


def does_gs_file_exist(file_path, user=None):
    process = _run_gsutil_command('ls', file_path, user=user)
    success = process.wait() == 0
    if not success:
        errors = [line.decode('utf-8').strip() for line in process.stdout]
        logger.warning(' '.join(errors), user)
    return success


def google_bucket_file_iter(gs_path, byte_range=None, raw_content=False, user=None, **kwargs):
    range_arg = ' -r {}-{}'.format(byte_range[0], byte_range[1]) if byte_range else ''
    process = _run_gsutil_command(
        'cat{}'.format(range_arg), gs_path, gunzip=gs_path.endswith("gz") and not raw_content, user=user, **kwargs)
    for line in process.stdout:
        if not raw_content:
            line = line.decode('utf-8')
        yield line


def mv_file_to_gs(local_path, gs_path, user=None):
    command = 'mv {}'.format(local_path)
    _run_gsutil_with_wait(command, gs_path, user)
    
    
def cp_file_from_gs(gs_path, local_dir, user):
    bucket_name, blob_name = _parse_gs_path(gs_path)
    local_path = os.path.join(local_dir, os.path.basename(blob_name))

    bucket = storage.Client().bucket(bucket_name, user_project=get_google_project(gs_path))
    bucket.blob(blob_name).download_to_filename(local_path)


def get_gs_file_list(gs_path, user, check_subfolders, allow_missing):
    gs_path = gs_path.rstrip('/')
    command = 'ls'

    if check_subfolders:
        # If a bucket is empty gsutil throws an error when running ls with ** instead of returning an empty list
        subfolders = _run_gsutil_with_stdout(command, gs_path.replace('/**', ''), user)
        if not subfolders:
            return []

    all_lines = _run_gsutil_with_stdout(command, gs_path, user, allow_missing=allow_missing)
    return [line for line in all_lines if is_google_bucket_file_path(line)]


def _run_gsutil_with_wait(command, gs_path, user=None, **kwargs):
    process = _run_gsutil_command(command, gs_path, user=user, **kwargs)
    if process.wait() != 0:
        errors = [line.decode('utf-8').strip() for line in process.stdout]
        raise Exception('Run command failed: ' + ' '.join(errors))
    return process


def _run_gsutil_with_stdout(command, gs_path, user=None, allow_missing=False):
    process = _run_gsutil_command(command, gs_path, user=user, pipe_errors=True)
    output, errs = process.communicate()
    if errs:
        errors = errs.decode('utf-8').strip().replace('\n', ' ')
        if allow_missing:
            logger.info(errors, user)
        else:
            raise Exception(f'Run command failed: {errors}')
    return [line for line in output.decode('utf-8').split('\n') if line]
