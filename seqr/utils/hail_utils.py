import logging
import os

from seqr.utils.file_utils import does_file_exist
from seqr.utils.gcloud.google_dataproc_hail_utils import DataprocHailRunner
from seqr.utils.local.local_hail_utils import LocalHailRunner
from settings import BASE_DIR, ELASTICSEARCH_HOST, ELASTICSEARCH_PORT

logger = logging.Logger(__name__)


class HailRunner():

    def __init__(self, cluster_id, genome_version):
        self.genome_version = genome_version

        if "running on cloud":
            self.hail_runner = DataprocHailRunner(cluster_id)
        else:
            self.hail_runner = LocalHailRunner()

    def initialize(self):
        self.hail_runner.init_runner(self.genome_version, synchronous=True)

    def delete(self):
        self.hail_runner.delete_runner(synchronous=True)

    def __enter__(self):
        return self.initialize()

    def __exit__(self, exc_type, exc_value, traceback):
        return self.delete()

    def run_vep(self, input_vcf_path, output_vds_path):
        """Run VEP on the dataset. Assumes the dataproc cluster already exists."""

        if not does_file_exist(input_vcf_path):
            raise ValueError("%(input_vcf_path)s not foud" % locals())

        script_path = os.path.join(BASE_DIR, "seqr/pipelines/hail/run_vep.py")
        script_args = [
            input_vcf_path,
            output_vds_path,
        ]

        self.run_hail(script_path, *script_args)

    def export_to_elasticsearch(self, vds_path, dataset_id, dataset_type, genome_version):
        """Export the dataset to elasticsearch. Assumes the dataproc cluster already exists.

        Args:
            vds_path (string):
            dataset_id (string):
            dataset_type (string):
            genome_version (string): "37" or "38"
        """

        #elasticsearch_host_ip = self._get_k8s_resource_name("pods", labels={'name': 'elasticsearch'}, json_path=".items[0].status.hostIP")
        #solr_node_name = self._get_k8s_resource_name("pods", labels={'name': 'solr'}, json_path=".items[0].spec.nodeName")

        script_path = os.path.join(BASE_DIR, "seqr/pipelines/hail/export_variants_to_ES.py")
        script_args=[
            "--host", ELASTICSEARCH_HOST,
            "--port", ELASTICSEARCH_PORT,
            "--genome-version", genome_version,
            "--index", dataset_id,
            "--index-type", dataset_type,
            vds_path,
        ]

        self._run_hail(script_path, *script_args)

