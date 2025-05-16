import glob
import gzip
import os
import subprocess # nosec

from seqr.utils.logging_utils import SeqrLogger

logger = SeqrLogger(__name__)


def run_command(command, user=None, pipe_errors=False):
    logger.info('==> {}'.format(command), user)
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE if pipe_errors else subprocess.STDOUT, shell=True) # nosec


def _run_gsutil_command(command, gs_path, gunzip=False, user=None, pipe_errors=False, no_project=False):
    if not is_google_bucket_file_path(gs_path):
        raise Exception('A Google Storage path is expected.')

    #  Anvil buckets are requester-pays and we bill them to the anvil project
    google_project = get_google_project(gs_path) if not no_project else None
    project_arg = '-u {} '.format(google_project) if google_project else ''
    command = 'gsutil {project_arg}{command} {gs_path}'.format(
        project_arg=project_arg, command=command, gs_path=gs_path,
    )
    if gunzip:
        command += " | gunzip -c -q - "

    return run_command(command, user=user, pipe_errors=pipe_errors)


def is_google_bucket_file_path(file_path):
    return file_path.startswith("gs://")


def get_google_project(gs_path):
    return 'anvil-datastorage' if gs_path.startswith('gs://fc-secure') else None


def does_file_exist(file_path, user=None):
    if is_google_bucket_file_path(file_path):
        process = _run_gsutil_command('ls', file_path, user=user)
        success = process.wait() == 0
        if not success:
            errors = [line.decode('utf-8').strip() for line in process.stdout]
            logger.info(' '.join(errors), user)
        return success
    return os.path.isfile(file_path)


def list_files(wildcard_path, user, check_subfolders=False, allow_missing=True):
    if check_subfolders:
        wildcard_path = f'{wildcard_path.rstrip("/")}/**'
    if is_google_bucket_file_path(wildcard_path):
        return _get_gs_file_list(wildcard_path, user, check_subfolders, allow_missing)
    return [file_path for file_path in glob.glob(wildcard_path, recursive=check_subfolders) if os.path.isfile(file_path)]


def file_iter(file_path, byte_range=None, raw_content=False, user=None, **kwargs):
    if is_google_bucket_file_path(file_path):
        for line in _google_bucket_file_iter(file_path, byte_range=byte_range, raw_content=raw_content, user=user, **kwargs):
            yield line
    elif byte_range:
        command = 'dd skip={offset} count={size} bs=1 if={file_path} status="none"'.format(
            offset=byte_range[0],
            size=byte_range[1]-byte_range[0] + 1,
            file_path=file_path,
        )
        if file_path.endswith("gz"):
            command += " | gunzip -c - "
        process = run_command(command, user=user)
        for line in process.stdout:
            yield line
    else:
        mode = 'rb' if raw_content else 'r'
        open_func = gzip.open if file_path.endswith("gz") else open
        with open_func(file_path, mode) as f:
            for line in f:
                yield line


def _google_bucket_file_iter(gs_path, byte_range=None, raw_content=False, user=None, **kwargs):
    """Iterate over lines in the given file"""
    range_arg = ' -r {}-{}'.format(byte_range[0], byte_range[1]) if byte_range else ''
    process = _run_gsutil_command(
        'cat{}'.format(range_arg), gs_path, gunzip=gs_path.endswith("gz") and not raw_content, user=user, **kwargs)
    for line in process.stdout:
        if not raw_content:
            line = line.decode('utf-8')
        yield line


def mv_file_to_gs(local_path, gs_path, user=None):
    command = 'mv {}'.format(local_path)
    run_gsutil_with_wait(command, gs_path, user)


def _get_gs_file_list(gs_path, user, check_subfolders, allow_missing):
    gs_path = gs_path.rstrip('/')
    command = 'ls'

    if check_subfolders:
        # If a bucket is empty gsutil throws an error when running ls with ** instead of returning an empty list
        subfolders = _run_gsutil_with_stdout(command, gs_path.replace('/**', ''), user)
        if not subfolders:
            return []

    all_lines = _run_gsutil_with_stdout(command, gs_path, user, allow_missing=allow_missing)
    return [line for line in all_lines if is_google_bucket_file_path(line)]


def run_gsutil_with_wait(command, gs_path, user=None):
    process = _run_gsutil_command(command, gs_path, user=user)
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
