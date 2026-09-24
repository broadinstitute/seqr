import gzip
import os
import re
import subprocess # nosec

from google.cloud import storage

from seqr.utils.logging_utils import SeqrLogger

logger = SeqrLogger(__name__)


def _parse_gs_path(gs_path, no_project=False):
    if not is_google_bucket_file_path(gs_path):
        raise Exception('A Google Storage path is expected.')
    bucket_name, path = gs_path.replace('gs://', '', 1).split('/', 1)
    user_project = get_google_project(gs_path) if not no_project else None
    bucket = storage.Client().bucket(bucket_name, user_project=user_project)
    return bucket, path


def _get_gs_blob(gs_path, no_project=False):
    bucket, blob_name = _parse_gs_path(gs_path, no_project=no_project)
    return bucket.blob(blob_name)


def _run_gsutil_command(command, gs_path, gunzip=False, user=None, no_project=False):
    if not is_google_bucket_file_path(gs_path):
        raise Exception('A Google Storage path is expected.')

    #  Anvil buckets are requester-pays and we bill them to the anvil project
    google_project = get_google_project(gs_path) if not no_project else None
    project_arg = '-u {} '.format(google_project) if google_project else ''
    command = f'gsutil {project_arg}{command} {gs_path}'
    if gunzip:
        command += " | gunzip -c -q - "

    logger.info('==> {}'.format(command), user)
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True) # nosec


def is_google_bucket_file_path(file_path):
    return file_path.startswith("gs://")


def get_google_project(gs_path):
    return 'anvil-datastorage' if gs_path.startswith('gs://fc-secure') else None


def does_gs_file_exist(file_path):
    return _get_gs_blob(file_path).exists()


def google_bucket_file_stream(no_project):
    def wrapper(gs_path, mode):
        blob = _get_gs_blob(gs_path, no_project=no_project)
        return blob.open(mode)
    return wrapper

def google_bucket_file_bytes_iter(gs_path, first_byte, last_byte, raw_content=False, user=None):
    process = _run_gsutil_command(
        f'cat -r {first_byte}-{last_byte}', gs_path, gunzip=gs_path.endswith("gz") and not raw_content, user=user)
    for line in process.stdout:
        if not raw_content:
            line = line.decode('utf-8')
        yield line


def mv_file_to_gs(local_path, gs_path, user=None):
    command = 'mv {}'.format(local_path)
    _run_gsutil_with_wait(command, gs_path, user)
    
    
def cp_file_from_gs(gs_path, local_dir):
    blob = _get_gs_blob(gs_path)
    local_path = os.path.join(local_dir, os.path.basename(blob.name))
    blob.download_to_filename(local_path)


def get_gs_files(gs_path):
    bucket, prefix = _parse_gs_path(gs_path.rstrip('/'))
    return [f'gs://{bucket.name}/{blob.name}' for blob in bucket.list_blobs(prefix=f'{prefix}/')]


def get_gs_wildcard_match_files(gs_path):
    bucket, pattern = _parse_gs_path(gs_path)
    blobs = bucket.list_blobs(prefix=pattern.split('*')[0])
    regex = re.escape(pattern).replace(re.escape('*'), '.*')
    return [f'gs://{bucket.name}/{blob.name}' for blob in blobs if re.fullmatch(regex, blob.name)]


def _run_gsutil_with_wait(command, gs_path, user):
    process = _run_gsutil_command(command, gs_path, user=user)
    if process.wait() != 0:
        errors = [line.decode('utf-8').strip() for line in process.stdout]
        raise Exception('Run command failed: ' + ' '.join(errors))
    return process
