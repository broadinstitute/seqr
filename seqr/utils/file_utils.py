import logging
import os

from seqr.utils.gcloud.google_bucket_file_utils import is_google_bucket_file_path, \
    does_google_bucket_file_exist, google_bucket_file_iter, get_google_bucket_file_stats, \
    copy_google_bucket_file
from seqr.utils.local.local_file_utils import is_local_file_path, get_local_file_stats, \
    copy_local_file

logger = logging.getLogger(__name__)


def does_file_exist(file_path):
    if is_google_bucket_file_path(file_path):
        return does_google_bucket_file_exist(file_path)
    elif is_local_file_path(file_path):
        return os.path.isfile(file_path)
    else:
        raise ValueError("This type of file path is not supported: %(file_path)" % locals())


def file_iter(file_path):
    if is_google_bucket_file_path(file_path):
        for line in google_bucket_file_iter(file_path):
            yield line
    elif is_local_file_path(file_path):
        with open(file_path) as f:
            for line in f:
                yield line
    else:
        raise ValueError("This type of file path is not supported: %(file_path)" % locals())


def get_file_stats(file_path):
    if is_google_bucket_file_path(file_path):
        return get_google_bucket_file_stats(file_path)
    elif is_local_file_path(file_path):
        return get_local_file_stats(file_path)
    else:
        raise ValueError("This type of file path is not supported: %(file_path)" % locals())


def copy_file(source_file_path, dest_file_path):
    if is_local_file_path(source_file_path) and is_local_file_path(dest_file_path):
         return copy_local_file(source_file_path, dest_file_path)
    elif is_google_bucket_file_path(source_file_path) or is_google_bucket_file_path(dest_file_path):
        return copy_google_bucket_file(source_file_path, dest_file_path)
    else:
        raise ValueError("Copying from %(source_file_path)s to %(dest_file_path)s is not supported." % locals())


def inputs_older_than_outputs(inputs, outputs, label=""):
    def _get_file_ctime(file_path):
        file_stats = get_file_stats(file_path)
        return file_stats.ctime if file_stats else 0

    max_input_ctime = max(_get_file_ctime(input_path) for input_path in inputs)
    min_output_ctime = min(_get_file_ctime(output_path) for output_path in outputs)

    if max_input_ctime < min_output_ctime:
        logger.info(label + "output(s) (%s) up to date relative to input(s) (%s)" % (", ".join(outputs), ", ".join(inputs)))

    return max_input_ctime < min_output_ctime
