import logging
import os
import time

from seqr.pipelines.pipeline_utils import inputs_older_than_outputs
from seqr.utils.gcloud_utils import copy_file_to_gcloud
from seqr.utils.shell_utils import run_shell_command
from seqr.models import _slugify
from settings import BASE_DIR

logger = logging.getLogger(__name__)


class GCloudVariantPipeline:
    """Encapsulates the logic for using GCE dataproc cluster to annotate and load a variant callset
    into the variant store
    """

    def __init__(self, dataset):
        """
        Args:
             dataset (object): The variant callset to run through the pipeline
        """
        self.dataset_id = dataset.dataset_id or dataset.guid

        # from gcloud error message: clusterName must be a match of regex '(?:[a-z](?:[-a-z0-9]{0,49}[a-z0-9])?).'
        self.cluster_id = "c"+_slugify(self.dataset_id).replace("_", "-").lower()

        self.source_file_path = dataset.source_file_path
        self.source_filename = os.path.basename(dataset.source_file_path)

        self.genome_version = dataset.project.genome_version
        self.genome_version_label="GRCh%s" % self.genome_version

        self.dataset_directory = "gs://seqr-datasets/%(genome_version_label)s/%(dataset_id)s" % self.__dict__

        self.raw_vcf_path = "%(dataset_directory)s/%(source_filename)s" % self.__dict__
        self.vep_annotated_vds_path = "%(dataset_directory)s/%(dataset_id)s.vep.vds" % self.__dict__

    def get_dataset_directory(self):
        return self.dataset_directory

    def run_pipeline(self):
        """Create a dataproc cluster and run the annotation and loading pipeline on the dataset provided to the constructor"""
        if not inputs_older_than_outputs([self.source_file_path], [self.raw_vcf_path], label="copy step: "):
            logger.info("copy step: copying %s to %s" % (self.source_file_path, self.raw_vcf_path))
            copy_file_to_gcloud(self.source_file_path, self.raw_vcf_path)

        vds_file = os.path.join(self.vep_annotated_vds_path, "metadata.json.gz")  # stat only works on files, not directories
        if not inputs_older_than_outputs([self.raw_vcf_path], [vds_file], label="vep annotation step: "):
            logger.info("vep annotation step: annotating %s and outputing to %s" % (self.raw_vcf_path, vds_file))
            #self._delete_dataproc_cluster(synchronous=True)  # if the cluster already exists, delete it to clear any running jobs
            self._create_dataproc_cluster(synchronous=True)
            self._run_vep()


        self._create_dataproc_cluster(synchronous=True)
        self._export_to_solr()
        #self._delete_dataproc_cluster(synchronous=True)

    def _get_dataproc_cluster_status(self):
        """Return cluster status (eg. "CREATING", "RUNNING", etc."""

        _, output, _ = run_shell_command(
            """gcloud dataproc clusters list --filter='clusterName = %(cluster_id)s' --format='value(status.state)'""" % self.__dict__,
            wait_and_return_log_output=True, verbose=False)

        return output.strip()

    def _create_dataproc_cluster(self, synchronous=False):
        """Run "gcloud dataproc clusters create" to create a cluster for processing this dataset

        Args:
            synchronous (bool): Whether to wait until the cluster is created before returning.
        """

        cluster_id = self.cluster_id
        async_arg = "" if synchronous else "--async"
        genome_version_label = self.genome_version_label

        run_shell_command(" ".join([
            "gcloud dataproc clusters create --async %(cluster_id)s",
                "--master-machine-type n1-highmem-4",
                "--master-boot-disk-size 100",
                "--num-workers 2",
                "--worker-machine-type n1-standard-4",
                "--worker-boot-disk-size 75",
                "--num-worker-local-ssds 1",
                "--num-preemptible-workers 5",
                "--image-version 1.1",
                "--properties", "'spark:spark.driver.extraJavaOptions=-Xss4M,spark:spark.executor.extraJavaOptions=-Xss4M,spark:spark.driver.memory=45g,spark:spark.driver.maxResultSize=30g,spark:spark.task.maxFailures=20,spark:spark.kryoserializer.buffer.max=1g,hdfs:dfs.replication=1'",
                "--initialization-actions", "gs://hail-common/hail-init.sh,gs://hail-common/vep/vep/%(genome_version_label)s/vep85-%(genome_version_label)s-init.sh",
            ]) % locals()).wait()

        # wait for cluster to initialize. The reason this loop is necessary even when
        # "gcloud dataproc clusters create" is run without --async is that the dataproc clusters
        # create command exits with an error if the cluster already exists, even if it's not in a
        # RUNNING state. This loop makes sure that the cluster is Running before proceeding to the
        # next step in the pipeline.
        if synchronous:
            while True:
                cluster_status = self._get_dataproc_cluster_status()
                if cluster_status == "RUNNING":
                    logger.info("Cluster status: [%s]" % (cluster_status, ))
                    break

                logger.info("waiting for cluster %s - current status: [%s]" % (cluster_id, cluster_status, ))
                time.sleep(5)

    def _delete_dataproc_cluster(self, synchronous=False):
        """Delete the dataproc cluster created by self._create_dataproc_cluster(..)

        Args:
            synchronous (bool): Whether to wait for the deletion operation to complete before returning
        """
        cluster_id = self.cluster_id
        async_arg = "" if synchronous else "--async"

        run_shell_command(
            "gcloud dataproc clusters delete --quiet %(async_arg)s %(cluster_id)s" % locals()
        ).wait()

    def _run_vep(self):
        """Run VEP on the dataset. Assumes the dataproc cluster already exists."""

        script_path = os.path.join(BASE_DIR, "seqr/pipelines/hail/run_vep.py")
        self._run_hail(script_path, self.raw_vcf_path, self.vep_annotated_vds_path)

    def _export_to_solr(self):
        """Export the dataset to solr. Assumes the dataproc cluster already exists, and VEP annotation is complete."""

        solr_host_ip = self._get_k8s_resource_name("pods", labels={'name': 'solr'}, json_path=".items[0].status.hostIP")
        #solr_node_name = self._get_k8s_resource_name("pods", labels={'name': 'solr'}, json_path=".items[0].spec.nodeName")

        script_path = os.path.join(BASE_DIR, "seqr/pipelines/hail/run_annotation.py")
        self._run_hail(script_path, solr_host_ip, self.vep_annotated_vds_path, "-g", self.genome_version)

        #script_path = os.path.join(BASE_DIR, "seqr/pipelines/hail/scripts/export_to_solr.py")
        #self._run_hail(script_path, solr_host_ip, self.vep_annotated_vds_path)

        # #run_shell_command("curl 'http://%(SOLR_HOST)s:30002/solr/seqr_noref/select?indent=on&q=*:*&wt=json'" % locals()).wait()

    def _export_to_cassandra(self):
        """Export the dataset to cassandra. Assumes the dataproc cluster already exists, and VEP annotation is complete."""

        pod_name = self._get_k8s_resource_name("pods", labels={'name': 'cassandara'}, json_path=".items[0].metadata.name")

        run_shell_command("""
        kubectl exec -i %(pod_name)s -- cqlsh <<EOF
            DROP KEYSPACE IF EXISTS seqr;
            CREATE KEYSPACE seqr WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}  AND durable_writes = true;

            CREATE TABLE seqr.seqr (chrom text, start int, ref text, alt text, dataset_5fid text, PRIMARY KEY (chrom, start, ref, alt, dataset_5fid));
        EOF
        """ % locals()).wait()

        script_path = "scripts/loading/export_to_cass.py"
        #node_name = lookup_json_path("pods", labels={'name': 'cassandra'}, json_path=".items[0].spec.nodeName")
        cassandra_host_ip = self._get_k8s_resource_name("pods", labels={'name': 'cassandra'}, json_path=".items[0].status.hostIP")
        self._run_hail(script_path, cassandra_host_ip, self.vep_annotated_vds_path)

        run_shell_command("""
        kubectl exec -i %(pod_name)s -- cqlsh <<EOF
            select count(*) from seqr.seqr;
        EOF
        """ % locals()).wait()

    def _run_hail(self, script_path, *script_args):
        """Generic method for submitting a python hail script to pyspark.  Assumes the dataproc cluster already exists."""

        cluster_id = self.cluster_id

        _, hail_hash, _ = run_shell_command(
            "gsutil cat gs://hail-common/latest-hash.txt",
            wait_and_return_log_output=True)

        hail_hash = hail_hash.strip()
        hail_zip = "gs://hail-common/pyhail-hail-is-master-%(hail_hash)s.zip" % locals()
        hail_jar = "gs://hail-common/hail-hail-is-master-all-spark2.0.2-%(hail_hash)s.jar" % locals()
        hail_jar_filename = os.path.basename(hail_jar)
        script_args_string = " ".join(['"%s"' % a for a in script_args])
        run_shell_command(" ".join([
            "gcloud dataproc jobs submit pyspark",
              "--cluster=%(cluster_id)s",
              "--files=%(hail_jar)s",
              "--py-files=%(hail_zip)s",
              "--properties=spark.files=./%(hail_jar_filename)s,spark.driver.extraClassPath=./%(hail_jar_filename)s,spark.executor.extraClassPath=./%(hail_jar_filename)s",
              "%(script_path)s -- %(script_args_string)s"
            ]) % locals()).wait()

    def _get_k8s_resource_name(self, resource_type="pod", labels={}, json_path=".items[0].metadata.name"):
        """Runs 'kubectl get <resource_type>' command to retrieve the full name of this resource.

        Args:
            component (string): keyword to use for looking up a kubernetes entity (eg. 'phenotips' or 'nginx')
            labels (dict): (eg. {'name': 'solr'})
            json_path (string): a json path query string (eg. ".items[0].metadata.name")
        Returns:
            (string) resource value (eg. "postgres-410765475-1vtkn")
        """

        l_args = " ".join(['-l %s=%s' % (key, value) for key, value in labels.items()])
        _, output, _ = run_shell_command("kubectl get %(resource_type)s %(l_args)s -o jsonpath={%(json_path)s}" % locals(), wait_and_return_log_output=True)
        output = output.strip('\n')

        return output

