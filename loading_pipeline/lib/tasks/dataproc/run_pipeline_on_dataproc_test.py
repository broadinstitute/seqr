import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import google.api_core.exceptions
import google.cloud.dataproc_v1.types.jobs
import luigi

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.tasks.dataproc.run_pipeline_on_dataproc import (
    RunPipelineOnDataprocTask,
)
from loading_pipeline.lib.test.mock_complete_task import MockCompleteTask


@patch(
    'loading_pipeline.lib.tasks.dataproc.base_run_job_on_dataproc.CreateDataprocClusterTask',
)
@patch(
    'loading_pipeline.lib.tasks.dataproc.base_run_job_on_dataproc.dataproc.JobControllerClient',
)
class WriteSuccessFileOnDataprocTaskTest(unittest.TestCase):
    @patch('loading_pipeline.lib.tasks.dataproc.base_run_job_on_dataproc.logger')
    def test_job_already_exists_failed(
        self,
        mock_logger: Mock,
        mock_job_controller_client: Mock,
        mock_create_dataproc_cluster: Mock,
    ) -> None:
        mock_create_dataproc_cluster.return_value = MockCompleteTask()
        mock_client = mock_job_controller_client.return_value
        mock_client.get_job.return_value = SimpleNamespace(
            status=SimpleNamespace(
                state=google.cloud.dataproc_v1.types.jobs.JobStatus.State.ERROR,
                details='Google Cloud Dataproc Agent reports job failure. If logs are available, they can be found at...',
            ),
        )
        mock_client.submit_job_as_operation.side_effect = (
            google.api_core.exceptions.AlreadyExists('job exists')
        )
        worker = luigi.worker.Worker()
        task = RunPipelineOnDataprocTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path='test_callset',
            project_guids=['R0113_test_project'],
            run_id='manual__2024-04-03',
            attempt_id=0,
        )
        worker.add(task)
        worker.run()
        self.assertFalse(task.complete())
        mock_logger.error.assert_has_calls(
            [
                call(
                    'Job RunPipelineTask-38-SNV-INDEL-manual__2024-04-03-0 entered ERROR state',
                ),
            ],
        )

    def test_job_already_exists_success(
        self,
        mock_job_controller_client: Mock,
        mock_create_dataproc_cluster: Mock,
    ) -> None:
        mock_create_dataproc_cluster.return_value = MockCompleteTask()
        mock_client = mock_job_controller_client.return_value
        mock_client.get_job.return_value = SimpleNamespace(
            status=SimpleNamespace(
                state=google.cloud.dataproc_v1.types.jobs.JobStatus.State.DONE,
            ),
        )
        worker = luigi.worker.Worker()
        task = RunPipelineOnDataprocTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path='test_callset',
            project_guids=['R0113_test_project'],
            run_id='manual__2024-04-04',
            attempt_id=0,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.complete())

    @patch('loading_pipeline.lib.tasks.dataproc.base_run_job_on_dataproc.logger')
    def test_job_failed(
        self,
        mock_logger: Mock,
        mock_job_controller_client: Mock,
        mock_create_dataproc_cluster: Mock,
    ) -> None:
        mock_create_dataproc_cluster.return_value = MockCompleteTask()
        mock_client = mock_job_controller_client.return_value
        mock_client.get_job.side_effect = [
            google.api_core.exceptions.NotFound(
                'job not found',
            ),
            google.api_core.exceptions.NotFound(
                'job not found',
            ),
            SimpleNamespace(
                status=SimpleNamespace(
                    state=google.cloud.dataproc_v1.types.jobs.JobStatus.State.PENDING,
                ),
            ),
            SimpleNamespace(
                status=SimpleNamespace(
                    state=google.cloud.dataproc_v1.types.jobs.JobStatus.State.ERROR,
                ),
            ),
        ]
        worker = luigi.worker.Worker()
        task = RunPipelineOnDataprocTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path='test_callset',
            project_guids=['R0113_test_project'],
            run_id='manual__2024-04-05',
            attempt_id=1,
        )
        worker.add(task)
        luigi_task_result = worker.run()
        self.assertEqual(luigi_task_result, False)
        mock_logger.info.assert_has_calls(
            [
                call(
                    'Waiting for Job completion RunPipelineTask-38-SNV-INDEL-manual__2024-04-05-1',
                ),
            ],
        )

    @patch('loading_pipeline.lib.tasks.dataproc.base_run_job_on_dataproc.logger')
    def test_job_success(
        self,
        mock_logger: Mock,
        mock_job_controller_client: Mock,
        mock_create_dataproc_cluster: Mock,
    ) -> None:
        mock_create_dataproc_cluster.return_value = MockCompleteTask()
        mock_client = mock_job_controller_client.return_value
        mock_client.get_job.side_effect = [
            google.api_core.exceptions.NotFound(
                'job not found',
            ),
            google.api_core.exceptions.NotFound(
                'job not found',
            ),
            SimpleNamespace(
                status=SimpleNamespace(
                    state=google.cloud.dataproc_v1.types.jobs.JobStatus.State.PENDING,
                ),
            ),
            SimpleNamespace(
                status=SimpleNamespace(
                    state=google.cloud.dataproc_v1.types.jobs.JobStatus.State.DONE,
                ),
            ),
        ]
        worker = luigi.worker.Worker()
        task = RunPipelineOnDataprocTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SNV_INDEL,
            sample_type=SampleType.WGS,
            callset_path='test_callset',
            project_guids=['R0113_test_project'],
            run_id='manual__2024-04-06',
            attempt_id=0,
        )
        worker.add(task)
        worker.run()
        mock_logger.info.assert_has_calls(
            [
                call(
                    'Waiting for Job completion RunPipelineTask-38-SNV-INDEL-manual__2024-04-06-0',
                ),
                call(
                    'Job RunPipelineTask-38-SNV-INDEL-manual__2024-04-06-0 is complete',
                ),
            ],
        )
