import os
import subprocess

from seqr.utils.logging_utils import SeqrLogger

logger = SeqrLogger(__name__)


def _run_command(command, user=None):
    logger.info('==> {}'.format(command), user)
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)


def _run_gsutil_command(command, gs_path, gunzip=False, user=None):
    #  Anvil buckets are requester-pays and we bill them to the anvil project
    project_arg = '-u anvil-datastorage ' if gs_path.startswith('gs://fc-secure') else ''
    command = 'gsutil {project_arg}{command} {gs_path}'.format(
        project_arg=project_arg, command=command, gs_path=gs_path,
    )
    if gunzip:
        command += " | gunzip -c -q - "

    return _run_command(command, user=user)


def _is_google_bucket_file_path(file_path):
    return file_path.startswith("gs://")


def does_file_exist(file_path, user=None):
    if _is_google_bucket_file_path(file_path):
        process = _run_gsutil_command('ls', file_path, user=user)
        return process.wait() == 0
    return os.path.isfile(file_path)


def file_iter(file_path, byte_range=None, raw_content=False, user=None):
    if _is_google_bucket_file_path(file_path):
        for line in _google_bucket_file_iter(file_path, byte_range=byte_range, raw_content=raw_content, user=user):
            yield line
    elif byte_range:
        command = 'dd skip={offset} count={size} bs=1 if={file_path}'.format(
            offset=byte_range[0],
            size=byte_range[1]-byte_range[0],
            file_path=file_path,
        )
        process = _run_command(command, user=user)
        for line in process.stdout:
            yield line
    else:
        mode = 'rb' if raw_content else 'r'
        with open(file_path, mode) as f:
            for line in f:
                yield line


def _google_bucket_file_iter(gs_path, byte_range=None, raw_content=False, user=None):
    """Iterate over lines in the given file"""
    range_arg = ' -r {}-{}'.format(byte_range[0], byte_range[1]) if byte_range else ''
    process = _run_gsutil_command(
        'cat{}'.format(range_arg), gs_path, gunzip=gs_path.endswith("gz") and not raw_content, user=user)
    for line in process.stdout:
        if not raw_content:
            line = line.decode('utf-8')
        yield line


def get_vcf_filename(vcf_path):
    if vcf_path.endswith('.vcf') or vcf_path.endswith('.vcf.gz') or vcf_path.endswith('.vcf.bgz'):
        return vcf_path
    process = subprocess.Popen('gsutil ls ' + vcf_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    if process.wait() != 0:
        return None
    for line in process.stdout:
        file = line.decode('utf-8').strip()
        if file.endswith('.vcf') or file.endswith('.vcf.gz') or file.endswith('.vcf.bgz'):
            return file
    return None


def get_vcf_samples(vcf_path):
    vcf_filename = get_vcf_filename(vcf_path)
    if not vcf_filename:
        return {}
    for line in file_iter(vcf_filename, byte_range=(0, 65536)):
        if line.startswith('#CHROM'):
            return set(line.rstrip().split('\tFORMAT\t', 2)[1].split('\t') if line.endswith('\n') else [])
    return {}
