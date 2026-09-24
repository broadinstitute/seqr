import glob
import gzip
import os

from seqr.utils.google_storage_utils import is_google_bucket_file_path, does_gs_file_exist, google_bucket_file_iter, \
    get_gs_files, get_gs_wildcard_match_files


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


def file_iter(file_path, byte_range=None, raw_content=False, user=None, **kwargs):
    if not does_file_exist(file_path):
        raise FileNotFoundError(f'Could not access file {file_path}')
    if is_google_bucket_file_path(file_path):
        for line in google_bucket_file_iter(file_path, byte_range=byte_range, raw_content=raw_content, user=user, **kwargs):
            yield line
    elif byte_range:
        with open(file_path, 'rb') as f:
            f.seek(byte_range[0])
            data = f.read(byte_range[1] - byte_range[0]+1)
        if file_path.endswith('gz'):
            data = gzip.decompress(data)
        yield data
    else:
        mode = 'rb' if raw_content else 'r'
        is_gz = file_path.endswith("gz")
        open_func = gzip.open if is_gz else open
        with open_func(file_path, mode) as f:
            for line in f:
                if is_gz and not raw_content:
                    line = line.decode('utf-8')
                yield line
