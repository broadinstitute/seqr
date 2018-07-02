import os

from seqr.utils.other_utils import FileStats
from seqr.utils.shell_utils import run


def is_local_file_path(file_path):
    return "://" not in file_path


def get_local_file_stats(file_path):
    if not os.path.exists(file_path):
        return None

    return FileStats(
        ctime=os.path.getctime(file_path),
        mtime=os.path.getmtime(file_path),
        size=os.path.getsize(file_path),
        md5=None,
    )


def copy_local_file(dataset_file_path, dest_file_path):
    if not os.path.exists(dataset_file_path):
        raise ValueError("%(dataset_file_path)s not found" % locals())

    run("cp -r %(dataset_file_path)s %(dest_file_path)s" % locals())