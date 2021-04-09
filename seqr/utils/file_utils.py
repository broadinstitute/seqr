import logging
import os
import subprocess

import google.cloud.storage


logger = logging.getLogger(__name__)
gcs_client = None

ANVIL_BUCKET_PREFIX = 'fc-secure'
ANVIL_BILLING_PROJECT = 'anvil-datastorage'

def _gcs_client():
    """Returns a lazily initialized GCS storage client."""
    global gcs_client
    if not gcs_client:
        gcs_client = google.cloud.storage.Client()
    return gcs_client


def _run_gsutil_command(command, gs_path, gunzip=False):
    #  Anvil buckets are requester-pays and we bill them to the anvil project
    project_arg = f'-u {ANVIL_BILLING_PROJECT} ' if gs_path.startswith(f'gs://{ANVIL_BUCKET_PREFIX}') else ''
    command = 'gsutil {project_arg}{command} {gs_path}'.format(
        project_arg=project_arg, command=command, gs_path=gs_path,
    )
    if gunzip:
        command += " | gunzip -c -q - "

    logger.info('==> {}'.format(command))
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)


def _is_google_bucket_file_path(file_path):
    return file_path.startswith("gs://")


def does_file_exist(file_path):
    if _is_google_bucket_file_path(file_path):
        process = _run_gsutil_command('ls', file_path)
        return process.wait() == 0
    return os.path.isfile(file_path)


def file_iter(file_path, byte_range=None, raw_content=False):
    """Note: the byte_range interval end is inclusive, i.e. the length is 
    byte_range[1] - byte_range[0] + 1."""
    if _is_google_bucket_file_path(file_path):
        path_segments = file_path.split('/')
        if len(path_segments) < 4:
            raise ValueError(f'Invalid GCS path: "{file_path}"')
        user_project = ANVIL_BILLING_PROJECT if path_segments[2].startswith(ANVIL_BUCKET_PREFIX) else None
        bucket = _gcs_client().bucket(path_segments[2], user_project)
        blob = bucket.blob('/'.join(path_segments[3:]))
        current = byte_range[0] if byte_range else 0
        end = byte_range[1] if byte_range else None
        while True:
            chunk_end = current + (1 << 20) - 1  # 1 MB chunks
            if end and end < chunk_end:
                chunk_end = end
            data = blob.download_as_bytes(start=current, end=chunk_end, checksum=None)
            current += len(data)
            yield data if raw_content else data.decode('utf-8')
            # We're done if we couldn't read the full range or we've reached the end.
            if current <= chunk_end or (end and current > end):
                break
    else:
        mode = 'rb' if raw_content else 'r'
        with open(file_path, mode) as f:
            if byte_range:
                f.seek(byte_range[0])
                for line in f:
                    if f.tell() < byte_range[1]:
                        yield line
                    else:
                        break
            else:
                for line in f:
                    yield line
