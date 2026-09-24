import os
import re

from google.cloud import storage


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

def google_bucket_read_bytes(gs_path, first_byte, last_byte):
    blob = _get_gs_blob(gs_path)
    return blob.download_as_bytes(start=first_byte, end=last_byte)


def mv_file_to_gs(local_path, gs_path):
    blob = _get_gs_blob(gs_path)
    blob.upload_from_filename(local_path)
    os.remove(local_path)
    
    
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
