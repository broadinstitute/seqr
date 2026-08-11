import re
import time

import google.api_core.exceptions
import google.cloud.dataproc_v1.types.jobs
import luigi
from google.cloud import dataproc_v1 as dataproc

from loading_pipeline.lib.core import Env
from loading_pipeline.lib.logger import get_logger
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.dataproc.create_dataproc_cluster import (
    CreateDataprocClusterTask,
)
from loading_pipeline.lib.tasks.dataproc.misc import get_cluster_name, to_kebab_str_args

FAILURE_STATUSES = {
    google.cloud.dataproc_v1.types.jobs.JobStatus.State.CANCELLED,
    google.cloud.dataproc_v1.types.jobs.JobStatus.State.ERROR,
    google.cloud.dataproc_v1.types.jobs.JobStatus.State.ATTEMPT_FAILURE,
}
SEQR_PIPELINE_RUNNER_BUILD = f'gs://seqr-pipeline-runner-builds/{Env.DEPLOYMENT_TYPE}/{Env.PIPELINE_RUNNER_APP_VERSION}'
TIMEOUT_S = 172800  # 2 days

logger = get_logger(__name__)


@luigi.util.inherits(BaseLoadingPipelineParams)
class BaseRunJobOnDataprocTask(luigi.Task):
    run_id = luigi.Parameter()
    attempt_id = luigi.IntParameter()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = dataproc.JobControllerClient(
            client_options={
                'api_endpoint': f'{Env.GCLOUD_REGION}-dataproc.googleapis.com:443',
            },
        )

    @property
    def task(self):
        raise NotImplementedError

    @property
    def job_id(self):
        return f'{self.task.task_family}-{self.reference_genome[-2:]}-{re.sub("_", "-", self.dataset_type.value)}-{self.run_id}-{self.attempt_id}'

    def requires(self) -> [luigi.Task]:
        return [self.clone(CreateDataprocClusterTask)]

    def safely_get_job(
        self,
    ):
        try:
            job = self.client.get_job(
                request={
                    'project_id': Env.GCLOUD_PROJECT,
                    'region': Env.GCLOUD_REGION,
                    'job_id': self.job_id,
                },
            )
        except google.api_core.exceptions.NotFound:
            return None
        else:
            return job

    def complete(self) -> bool:
        job = self.safely_get_job()
        if not job:
            return False
        if job.status.state in FAILURE_STATUSES:
            msg = f'Job {self.job_id} entered {job.status.state.name} state'
            logger.error(msg)
            logger.error(job.status.details)
        return (
            job.status.state == google.cloud.dataproc_v1.types.jobs.JobStatus.State.DONE
        )

    def run(self):
        job = self.safely_get_job()
        # Delete the job if it exists and was failed.  This handles manual re-runs of the
        # same run_id.
        if job and job.status.state in FAILURE_STATUSES:
            logger.error(
                f'Previous job {self.job_id} failed with state {job.status.state.name}',
            )
            logger.error(job.status.details)
            self.client.delete_job(
                request={
                    'project_id': Env.GCLOUD_PROJECT,
                    'region': Env.GCLOUD_REGION,
                    'job_id': self.job_id,
                },
            )
            job = None

        if not job:
            self.client.submit_job_as_operation(
                request={
                    'project_id': Env.GCLOUD_PROJECT,
                    'region': Env.GCLOUD_REGION,
                    'job': {
                        'reference': {
                            'job_id': self.job_id,
                        },
                        'placement': {
                            'cluster_name': get_cluster_name(
                                self.reference_genome,
                                self.run_id,
                            ),
                        },
                        'pyspark_job': {
                            'main_python_file_uri': f'{SEQR_PIPELINE_RUNNER_BUILD}/bin/run_task.py',
                            'args': [
                                self.task.task_family,
                                '--local-scheduler',
                                *to_kebab_str_args(self),
                            ],
                            'python_file_uris': [
                                f'{SEQR_PIPELINE_RUNNER_BUILD}/pyscripts.zip',
                            ],
                        },
                    },
                },
            )
        wait_s = 0
        while wait_s < TIMEOUT_S:
            job = self.safely_get_job()
            if (
                job.status.state
                == google.cloud.dataproc_v1.types.jobs.JobStatus.State.DONE
            ):
                msg = f'Job {self.job_id} is complete'
                logger.info(msg)
                break
            if job.status.state in FAILURE_STATUSES:
                msg = f'Job {self.job_id} entered {job.status.state.name} state'
                logger.error(msg)
                raise RuntimeError(msg)
            logger.info(
                f'Waiting for Job completion {self.job_id}',
            )
            time.sleep(3)
            wait_s += 3
