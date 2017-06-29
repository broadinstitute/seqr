import logging
import subprocess

from seqr.utils.shell_utils import run_shell_command

logger = logging.getLogger(__name__)

GCLOUD_RPOJECT='seqr-project'


def _run(command, verbose=False):
    if verbose:
        logger.info("Running: '%(command)s'" % locals())

    return subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT) #, env=full_env)


def does_file_exist(gs_path):

    result = _run("""
    gsutil stat %(gs_path)s
    """ % locals())

    logger.info(result)
    return result


def read_header(gs_path, header_prefix="#"):
    gunzip_command = "gunzip -c - | " if gs_path.endswith("gz") else ""

    header_content, _ = run_shell_command("""
    gsutil cat %(gs_path)s | %(gunzip_command)s head -n 5000 | grep ^%(header_prefix)s
    """ % locals(), wait_and_return_log_output=True, verbose=False)

    #logger.info(header_content)

    return header_content


def copy_file(gs_source, gs_destination):
    return None


def check_dataproc_cluster_status(assembly):
    pass


def create_dataproc_cluster(genome_build):
    # current cluster id for 37, 38

    GENOME_BUILD_LABEL="GRCh37"
    CLUSTER='seqr-pipeline-cluster-grch%(GENOME_BUILD_LABEL)s' % locals()

    """
    gcloud dataproc clusters create %(CLUSTER_ID)s  \
        --zone us-central1-b  \
        --master-machine-type n1-highmem-8  \
        --master-boot-disk-size 100  \
        --num-workers 2  \
        --worker-machine-type n1-highmem-8  \
        --worker-boot-disk-size 75  \
        --num-worker-local-ssds 1  \
        --num-preemptible-workers 4  \
        --image-version 1.1  \
        --project %(GCLOUD_PROJECT)s  \
        --properties "spark:spark.driver.extraJavaOptions=-Xss4M,spark:spark.executor.extraJavaOptions=-Xss4M,spark:spark.driver.memory=45g,spark:spark.driver.maxResultSize=30g,spark:spark.task.maxFailures=20,spark:spark.yarn.executor.memoryOverhead=30,spark:spark.kryoserializer.buffer.max=1g,hdfs:dfs.replication=1"  \
        --initialization-actions gs://hail-common/hail-init.sh,gs://hail-common/vep/vep/%(GENOME_BUILD_LABEL)s/vep85-%(GENOME_BUILD_LABEL)s-init.sh,gs://hail-common/init_notebook.py
    """ % locals()


def delete_dataproc_cluster(assembly):
    pass

