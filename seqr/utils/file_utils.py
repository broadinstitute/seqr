import logging
import os

from seqr.utils.gcloud.google_bucket_file_utils import is_google_bucket_file_path, \
    does_google_bucket_file_exist, google_bucket_file_iter

logger = logging.getLogger(__name__)


def is_local_file_path(file_path):
    return "://" not in file_path


def does_file_exist(file_path):
    if is_google_bucket_file_path(file_path):
        return does_google_bucket_file_exist(file_path)
    elif is_local_file_path(file_path):
        return os.path.isfile(file_path)
    else:
        raise ValueError("This type of file path is not supported: %(file_path)" % locals())


def file_iter(file_path, byte_range=None):
    if is_google_bucket_file_path(file_path):
        for line in google_bucket_file_iter(file_path, byte_range=byte_range):
            yield line
    elif is_local_file_path(file_path):
        with open(file_path) as f:
            if byte_range:
                f.seek(byte_range[0])
                while f.tell() < byte_range[1]:
                    for line in f:
                        yield line
            else:
                for line in f:
                    yield line
    else:
        raise ValueError("This type of file path is not supported: %(file_path)" % locals())
