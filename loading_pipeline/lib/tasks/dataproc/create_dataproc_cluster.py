import time

import google.api_core.exceptions
import google.cloud.dataproc_v1.types.clusters
import hail as hl
import luigi
from google.cloud import dataproc_v1 as dataproc
from pip._internal.operations import freeze as pip_freeze

from loading_pipeline.lib.core import DatasetType, Env, FeatureFlag, ReferenceGenome
from loading_pipeline.lib.logger import get_logger
from loading_pipeline.lib.misc.gcp import get_service_account_credentials
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.dataproc.misc import get_cluster_name

DEBIAN_IMAGE = '2.3.17-debian12'
DISK_SIZE_GB = 600
DISK_TYPE = 'hyperdisk-balanced'
HAIL_VERSION = hl.version().split('-')[0]
INSTANCE_TYPE = 'n4-highmem-8'
PKGS = '|'.join(
    [
        x.replace('gnomad_qc @ ', '').replace('onnxconverter-common @ ', '')
        for x in pip_freeze.freeze()
        if 'hail @' not in x
    ],
)
TIMEOUT_S = 1200
FAILURE_STATUSES = {
    google.cloud.dataproc_v1.types.clusters.ClusterStatus.State.UNKNOWN,
    google.cloud.dataproc_v1.types.clusters.ClusterStatus.State.ERROR,
    google.cloud.dataproc_v1.types.clusters.ClusterStatus.State.ERROR_DUE_TO_UPDATE,
}

logger = get_logger(__name__)


def get_cluster_config(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
):
    service_account_credentials = get_service_account_credentials()
    return {
        'project_id': Env.GCLOUD_PROJECT,
        'cluster_name': get_cluster_name(reference_genome, run_id),
        # Schema found at https://cloud.google.com/dataproc/docs/reference/rest/v1/ClusterConfig
        'config': {
            'gce_cluster_config': {
                'metadata': {
                    'WHEEL': f'gs://hail-common/hailctl/dataproc/{HAIL_VERSION}/hail-{HAIL_VERSION}-py3-none-any.whl',
                    'PKGS': PKGS,
                    'DEPLOYMENT_TYPE': Env.DEPLOYMENT_TYPE,
                    'REFERENCE_GENOME': reference_genome.value,
                    'PIPELINE_RUNNER_APP_VERSION': Env.PIPELINE_RUNNER_APP_VERSION,
                    'REFERENCE_DATASETS_DIR': Env.REFERENCE_DATASETS_DIR,
                },
                'internal_ip_only': False,  # Recent change with 2.2 dataproc images.
                'service_account': service_account_credentials.service_account_email,
                'service_account_scopes': service_account_credentials.scopes,
            },
            'master_config': {
                'num_instances': 1,
                'machine_type_uri': INSTANCE_TYPE,
                'disk_config': {
                    'boot_disk_type': DISK_TYPE,
                    'boot_disk_size_gb': DISK_SIZE_GB,
                },
            },
            'worker_config': {
                'num_instances': dataset_type.dataproc_primary_workers,
                'machine_type_uri': INSTANCE_TYPE,
                'disk_config': {
                    'boot_disk_type': DISK_TYPE,
                    'boot_disk_size_gb': DISK_SIZE_GB,
                },
            },
            'secondary_worker_config': {
                'num_instances': dataset_type.dataproc_preemptibles,
                'machine_type_uri': INSTANCE_TYPE,
                'disk_config': {
                    'boot_disk_type': DISK_TYPE,
                    'boot_disk_size_gb': DISK_SIZE_GB,
                },
                'is_preemptible': True,
                'preemptibility': 'PREEMPTIBLE',
            },
            'software_config': {
                'image_version': DEBIAN_IMAGE,
                'properties': {
                    'spark:spark.driver.maxResultSize': '0',
                    'spark:spark.task.maxFailures': '20',
                    'spark:spark.kryoserializer.buffer.max': '2g',
                    'spark:spark.driver.extraJavaOptions': '-Xss16M',
                    'spark:spark.executor.extraJavaOptions': '-Xss16M',
                    'hdfs:dfs.replication': '1',
                    'dataproc:dataproc.logging.stackdriver.enable': 'false',
                    'dataproc:dataproc.monitoring.stackdriver.enable': 'false',
                    'spark:spark.driver.memory': '41g',
                    'yarn:yarn.nodemanager.resource.memory-mb': '50585',
                    'yarn:yarn.scheduler.maximum-allocation-mb': '25292',
                    'spark:spark.executor.cores': '4',
                    'spark:spark.executor.memory': '10117m',
                    'spark:spark.executor.memoryOverhead': '15175m',
                    'spark:spark.memory.storageFraction': '0.2',
                    'spark:spark.executorEnv.HAIL_WORKER_OFF_HEAP_MEMORY_PER_CORE_MB': '6323',
                    'spark:spark.speculation': 'true',
                    'spark-env:CHECK_SEX_AND_RELATEDNESS': '1'
                    if FeatureFlag.CHECK_SEX_AND_RELATEDNESS
                    else '0',
                    'spark-env:EXPECT_TDR_METRICS': '1'
                    if FeatureFlag.EXPECT_TDR_METRICS
                    else '0',
                    'spark-env:PIPELINE_DATA_DIR': Env.PIPELINE_DATA_DIR,
                    'spark-env:HAIL_TMP_DIR': Env.HAIL_TMP_DIR,
                    'spark-env:LOADING_DATASETS_DIR': Env.LOADING_DATASETS_DIR,
                    'spark-env:REFERENCE_DATASETS_DIR': Env.REFERENCE_DATASETS_DIR,
                    'spark-env:SAMPLE_TYPE_VALIDATION_EXCLUDED_PROJECTS': ','.join(
                        Env.SAMPLE_TYPE_VALIDATION_EXCLUDED_PROJECTS,
                    ),
                },
            },
            'lifecycle_config': {'idle_delete_ttl': {'seconds': 1200}},
            'encryption_config': {},
            'autoscaling_config': {},
            'endpoint_config': {},
            'initialization_actions': [
                {
                    # NB: this script initializes the python env.
                    'executable_file': f'gs://hail-common/hailctl/dataproc/{HAIL_VERSION}/init_notebook.py',
                    'execution_timeout': {'seconds': 1200},
                },
                {
                    'executable_file': f'gs://seqr-pipeline-runner-builds/{Env.DEPLOYMENT_TYPE}/{Env.PIPELINE_RUNNER_APP_VERSION}/bin/dataproc_vep_init.bash',
                    'execution_timeout': {'seconds': 1200},
                },
            ],
        },
    }


@luigi.util.inherits(BaseLoadingPipelineParams)
class CreateDataprocClusterTask(luigi.Task):
    # NB: The luigi.dataproc.contrib module was old and bad
    # so we built our own shim.
    run_id = luigi.Parameter()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # https://cloud.google.com/dataproc/docs/tutorials/python-library-example
        self.client = dataproc.ClusterControllerClient(
            client_options={
                'api_endpoint': f'{Env.GCLOUD_REGION}-dataproc.googleapis.com:443',
            },
        )

    def safely_get_cluster(
        self,
    ):
        try:
            cluster = self.client.get_cluster(
                request={
                    'project_id': Env.GCLOUD_PROJECT,
                    'region': Env.GCLOUD_REGION,
                    'cluster_name': get_cluster_name(
                        self.reference_genome,
                        self.run_id,
                    ),
                },
            )
        except google.api_core.exceptions.NotFound:
            return None
        else:
            return cluster

    def complete(self) -> bool:
        cluster = self.safely_get_cluster()
        if not cluster:
            return False
        if cluster.status.state in FAILURE_STATUSES:
            msg = f'Cluster {cluster.cluster_name} entered {cluster.status.state.name} state'
            logger.error(msg)
        # This will return False when the cluster is "CREATING"
        return (
            cluster.status.state
            == google.cloud.dataproc_v1.types.clusters.ClusterStatus.State.RUNNING
        )

    def run(self):
        if not Env.GCLOUD_PROJECT or not Env.GCLOUD_REGION:
            msg = 'Environment Variables GCLOUD_PROJECT and GCLOUD_REGION are required for running the pipeline on dataproc.'
            raise RuntimeError(msg)
        cluster = self.safely_get_cluster()
        if not cluster:
            self.client.create_cluster(
                request={
                    'project_id': Env.GCLOUD_PROJECT,
                    'region': Env.GCLOUD_REGION,
                    'cluster': get_cluster_config(
                        self.reference_genome,
                        self.dataset_type,
                        self.run_id,
                    ),
                },
            )
        wait_s = 0
        while wait_s < TIMEOUT_S:
            cluster = self.safely_get_cluster()
            if (
                cluster.status.state
                == google.cloud.dataproc_v1.types.clusters.ClusterStatus.State.RUNNING
            ):
                msg = f'Created cluster {cluster.cluster_name} with cluster uuid: {cluster.cluster_uuid}'
                logger.info(msg)
                break
            if cluster.status.state in FAILURE_STATUSES:
                msg = f'Cluster {cluster.cluster_name} entered {cluster.status.state.name} state'
                logger.error(msg)
                raise RuntimeError(msg)
            logger.info('Waiting for cluster spinup')
            time.sleep(3)
            wait_s += 3
