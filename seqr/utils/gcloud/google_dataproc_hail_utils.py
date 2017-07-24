import glob
import logging
import os
import tempfile
import time
import zipfile

from seqr.models import _slugify
from seqr.utils.shell_utils import run_shell_command
from settings import GCLOUD_PROJECT, GCLOUD_ZONE, BASE_DIR

logger = logging.getLogger(__name__)


class DataprocHailRunner:

    def __init__(self, cluster_id):
        """
        Args:
             cluster_id (string): unique id for the dataproc cluster.
        """

        # from gcloud error message: clusterName must be a match of regex '(?:[a-z](?:[-a-z0-9]{0,49}[a-z0-9])?).'
        self.cluster_id = "c"+_slugify(cluster_id).replace("_", "-").lower()

    def run_hail(self, script_path, *script_args):
        """Submits the hail script to dataproc.  Assumes cluster has already been created.

        Args:
            script_path (string):
            script_args (list): arguments to pass to the script
        """

        cluster_id = self.cluster_id

        #_, hail_hash, _ = run_shell_command(
        #    "gsutil cat gs://hail-common/latest-hash.txt",
        #    wait_and_return_log_output=True)
        #hail_hash = hail_hash.strip()
        #hail_zip = "gs://hail-common/pyhail-hail-is-master-%(hail_hash)s.zip" % locals()
        #hail_jar = "gs://hail-common/hail-hail-is-master-all-spark2.0.2-%(hail_hash)s.jar" % locals()

        hail_zip = "gs://gnomad-bw2/hail-jar/hail-python.zip"
        hail_jar = "gs://gnomad-bw2/hail-jar/hail-all-spark.jar"
        hail_jar_filename = os.path.basename(hail_jar)

        with tempfile.NamedTemporaryFile("w", suffix=".zip") as utils_zip:
            utils_zip_file_path = utils_zip.name
            with zipfile.ZipFile(utils_zip_file_path, "w") as utils_zip_file:
                for utils_script in glob.glob(os.path.join(BASE_DIR, "seqr/pipelines/hail/utils/*.py")):
                    utils_zip_file.write(utils_script, "utils/"+os.path.basename(utils_script))

            script_args_string = " ".join(script_args)
            run_shell_command(" ".join([
                "gcloud dataproc jobs submit pyspark",
                "--project", GCLOUD_PROJECT,
                "--cluster", cluster_id,
                "--files", hail_jar,
                "--py-files %(hail_zip)s,%(utils_zip_file_path)s",
                "--properties=spark.files=./%(hail_jar_filename)s,spark.driver.extraClassPath=./%(hail_jar_filename)s,spark.executor.extraClassPath=./%(hail_jar_filename)s",
                "%(script_path)s -- %(script_args_string)s"
            ]) % locals()).wait()

    def init_runner(
            self,
            genome_version,
            machine_type="n1-highmem-4",
            num_workers=2,
            num_preemptible_workers=5,
            synchronous=False):

        """Create a data-proc cluster.

        Args:
            genome_version (string): "37" or "38"
            machine_type (string): google cloud machine type
            num_workers (int):
            num_preemptible_workers (int):
            synchronous (bool): Whether to wait until the cluster is created before returning.
        """

        cluster_id = self.cluster_id
        genome_version_label = "GRCh%s" % genome_version

        # gs://hail-common/vep/vep/GRCh%(genome_version)s/vep85-GRCh%(genome_version)s-init.sh
        run_shell_command(" ".join([
            "gcloud dataproc clusters create %(cluster_id)s",
            "--project", GCLOUD_PROJECT,
            "--zone", GCLOUD_ZONE,
            "--master-machine-type", machine_type,
            "--master-boot-disk-size 100",
            "--num-workers 2",
            "--worker-machine-type", machine_type,
            "--worker-boot-disk-size 100",
            "--num-preemptible-workers %(num_preemptible_workers)s",
            "--image-version 1.1",
            "--properties", "spark:spark.driver.extraJavaOptions=-Xss4M,spark:spark.executor.extraJavaOptions=-Xss4M,spark:spark.driver.memory=45g,spark:spark.driver.maxResultSize=30g,spark:spark.task.maxFailures=20,spark:spark.yarn.executor.memoryOverhead=30,spark:spark.kryoserializer.buffer.max=1g,hdfs:dfs.replication=1",
            "--initialization-actions", "gs://hail-common/hail-init.sh,gs://hail-common/vep/vep/%(genome_version_label)s/vep85-%(genome_version_label)s-init.sh",
        ]) % locals()).wait()

        # wait for cluster to initialize. The reason this loop is necessary even when
        # "gcloud dataproc clusters create" is run without --async is that the dataproc clusters
        # create command exits with an error if the cluster already exists, even if it's not in a
        # RUNNING state. This loop makes sure that the cluster is Running before proceeding.
        if synchronous:
            while True:
                cluster_status = self._get_dataproc_cluster_status()
                if cluster_status == "RUNNING":
                    logger.info("cluster status: [%s]" % (cluster_status, ))
                    break

                logger.info("waiting for cluster %(cluster_id)s - current status: [%(cluster_status)s]" % locals())
                time.sleep(5)

    def delete_runner(self, synchronous=False):
        """Delete the dataproc cluster created by self._create_dataproc_cluster(..)

        Args:
            synchronous (bool): Whether to wait for the deletion operation to complete before returning
        """
        cluster_id = self.cluster_id
        async_arg = "" if synchronous else "--async"

        run_shell_command(" ".join([
            "gcloud dataproc clusters delete %(cluster_id)s",
                "--project", GCLOUD_PROJECT,
                "--quiet",
            ]) % locals()).wait()

    def _get_dataproc_cluster_status(self):
        """Return cluster status (eg. "CREATING", "RUNNING", etc."""
        cluster_id = self.cluster_id

        _, output, _ = run_shell_command(" ".join([
            "gcloud dataproc clusters list ",
                "--project", GCLOUD_PROJECT,
                "--filter", "'clusterName=%(cluster_id)s'",
                "--format", "'value(status.state)'"
            ]) % locals(),
            wait_and_return_log_output=True,
            verbose=False)

        return output.strip()

    def _get_k8s_resource_name(self, resource_type="pod", labels={}, json_path=".items[0].metadata.name"):
        """Runs 'kubectl get <resource_type>' command to retrieve the full name of this resource.

        Args:
            component (string): keyword to use for looking up a kubernetes entity (eg. 'phenotips' or 'nginx')
            labels (dict): (eg. {'name': 'phenotips'})
            json_path (string): a json path query string (eg. ".items[0].metadata.name")
        Returns:
            (string) resource value (eg. "postgres-410765475-1vtkn")
        """

        l_args = " ".join(['-l %s=%s' % (key, value) for key, value in labels.items()])
        _, output, _ = run_shell_command(
            "kubectl get %(resource_type)s %(l_args)s -o jsonpath={%(json_path)s}" % locals(),
            wait_and_return_log_output=True)
        output = output.strip('\n')

        return output
