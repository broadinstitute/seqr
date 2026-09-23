import glob
import gzip
import os

from seqr.utils.google_storage_utils import is_google_bucket_file_path, does_gs_file_exist, get_gs_file_list, \
    google_bucket_file_iter


def does_file_exist(file_path):
    if is_google_bucket_file_path(file_path):
        return does_gs_file_exist(file_path)
    return os.path.isfile(file_path)


def list_files(wildcard_path, user, check_subfolders=False, allow_missing=True):
    if check_subfolders:
        wildcard_path = f'{wildcard_path.rstrip("/")}/**'
    if is_google_bucket_file_path(wildcard_path):
        return get_gs_file_list(wildcard_path, user, check_subfolders, allow_missing)
    return [file_path for file_path in glob.glob(wildcard_path, recursive=check_subfolders) if os.path.isfile(file_path)]


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
