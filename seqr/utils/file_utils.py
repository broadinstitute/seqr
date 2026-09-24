import glob
import gzip
import os

from seqr.utils.google_storage_utils import is_google_bucket_file_path, does_gs_file_exist, google_bucket_file_stream, \
    google_bucket_file_bytes_iter, get_gs_files, get_gs_wildcard_match_files


def does_file_exist(file_path):
    if is_google_bucket_file_path(file_path):
        return does_gs_file_exist(file_path)
    return os.path.isfile(file_path)


def list_files(files_dir):
    if is_google_bucket_file_path(files_dir):
        return get_gs_files(files_dir)
    return _list_local_wildcard_files(f'{files_dir.rstrip("/")}/**', recursive=True)


def list_wildcard_match_files(wildcard_path):
    if is_google_bucket_file_path(wildcard_path):
        return get_gs_wildcard_match_files(wildcard_path)
    return _list_local_wildcard_files(wildcard_path)


def _list_local_wildcard_files(wildcard_path, **kwargs):
    return [file_path for file_path in glob.glob(wildcard_path, **kwargs) if os.path.isfile(file_path)]


def file_iter(file_path, raw_content=False, user=None, no_project=False):
    if not does_file_exist(file_path):
        raise FileNotFoundError(f'Could not access file {file_path}')
    is_gz = file_path.endswith('gz')
    mode = 'rb' if raw_content or is_gz else 'r'
    file_stream = google_bucket_file_stream(no_project) if is_google_bucket_file_path(file_path) else open
    with file_stream(file_path, mode) as f:
        if is_gz:
            f = gzip.open(f, 'r' if raw_content else 'rt')
        for line in f:
            yield line


def file_bytes_iter(file_path, first_byte, last_byte, raw_content=False, user=None):
    if not does_file_exist(file_path):
        raise FileNotFoundError(f'Could not access file {file_path}')
    if is_google_bucket_file_path(file_path):
        for line in google_bucket_file_bytes_iter(file_path, first_byte, last_byte, raw_content=raw_content, user=user):
            yield line
    else:
        with open(file_path, 'rb') as f:
            f.seek(first_byte)
            data = f.read(last_byte - first_byte+1)
        if file_path.endswith('gz'):
            data = gzip.decompress(data)
        yield data
