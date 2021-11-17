import os
import subprocess

import google.cloud.storage

from seqr.utils.logging_utils import SeqrLogger

logger = SeqrLogger(__name__)
gcs_client = None

ANVIL_BUCKET_PREFIX = "fc-secure"
ANVIL_BILLING_PROJECT = "anvil-datastorage"


def _gcs_client():
    """Returns a lazily initialized GCS storage client."""
    global gcs_client
    if not gcs_client:
        gcs_client = google.cloud.storage.Client()
    return gcs_client


def run_command(command, user=None):
    logger.info('==> {}'.format(command), user)
    return subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
    )


def _run_gsutil_command(command, gs_path, gunzip=False, user=None):
    #  Anvil buckets are requester-pays and we bill them to the anvil project
    google_project = get_google_project(gs_path)
    project_arg = (
        f"-u {google_project} "
        if gs_path.startswith(f"gs://{ANVIL_BUCKET_PREFIX}")
        else ""
    )
    command = 'gsutil {project_arg}{command} {gs_path}'.format(
        project_arg=project_arg, command=command, gs_path=gs_path,
    )
    if gunzip:
        command += " | gunzip -c -q - "

    return run_command(command, user=user)


def is_google_bucket_file_path(file_path):
    return file_path.startswith("gs://")


def get_google_project(gs_path):
    return 'anvil-datastorage' if gs_path.startswith('gs://fc-secure') else None


def does_file_exist(file_path, user=None):
    if is_google_bucket_file_path(file_path):
        process = _run_gsutil_command('ls', file_path, user=user)
        return process.wait() == 0
    return os.path.isfile(file_path)


# pylint: disable=unused-argument
def file_iter(file_path, byte_range=None, raw_content=False, user=None):
    """Note: the byte_range interval end is inclusive, i.e. the length is
    byte_range[1] - byte_range[0] + 1."""
    if is_google_bucket_file_path(file_path):
        path_segments = file_path.split("/")
        if len(path_segments) < 4:
            raise ValueError(f'Invalid GCS path: "{file_path}"')
        user_project = (
            ANVIL_BILLING_PROJECT
            if path_segments[2].startswith(ANVIL_BUCKET_PREFIX)
            else None
        )
        bucket = _gcs_client().bucket(path_segments[2], user_project)
        blob = bucket.blob("/".join(path_segments[3:]))
        current = byte_range[0] if byte_range else 0
        end = byte_range[1] if byte_range else None
        prev_line = ''
        while True:
            chunk_end = current + (1 << 20) - 1  # 1 MB chunks
            if end and end < chunk_end:
                chunk_end = end
            data = blob.download_as_bytes(start=current, end=chunk_end, checksum=None)
            current += len(data)
            if raw_content:
                yield data
            else:
                # Using \n might be a bad assumption if nl is represented another way
                lines = data.decode("utf-8").strip("\n").split("\n")
                if len(lines) == 1:
                    # one reaally long line (or to the end)
                    prev_line = prev_line + lines[0]
                else:
                    yield prev_line + lines.pop(0)
                    prev_line = lines.pop(-1)
                    for line in lines:
                        yield line

            # We're done if we couldn't read the full range or we've reached the end.
            if current <= chunk_end or (end and current > end):
                yield prev_line
                break
    elif byte_range:
        command = 'dd skip={offset} count={size} bs=1 if={file_path}'.format(
            offset=byte_range[0],
            size=byte_range[1] - byte_range[0],
            file_path=file_path,
        )
        process = run_command(command, user=user)
        for line in process.stdout:
            yield line
    else:
        mode = 'rb' if raw_content else 'r'
        with open(file_path, mode) as f:
            for line in f:
                yield line


def mv_file_to_gs(local_path, gs_path, user=None):
    if not is_google_bucket_file_path(gs_path):
        raise Exception('A Google Storage path is expected.')
    command = 'mv {}'.format(local_path)
    process = _run_gsutil_command(command, gs_path, user=user)
    if process.wait() != 0:
        errors = [line.decode('utf-8').strip() for line in process.stdout]
        raise Exception('Run command failed: ' + ' '.join(errors))
