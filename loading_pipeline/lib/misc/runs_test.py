import os

from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.misc.runs import get_run_ids
from loading_pipeline.lib.paths import (
    clickhouse_load_fail_file_path,
    clickhouse_load_success_file_path,
    pipeline_run_success_file_path,
    runs_path,
)
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase


class RunsTest(MockedDatarootTestCase):
    def setUp(self):
        super().setUp()
        run_ids = [
            'manual__2024-08-05T16-07-58.365146+00-00',
            'manual__2024-08-06T10-15-23.123456+00-00',
            'manual__2024-08-07T12-30-45.654321+00-00',  # _SUCCESS, _CLICKHOUSE_LOAD_FAIL
            'manual__2024-08-08T09-45-00.000000+00-00',  # _SUCCESS
            'manual__2024-08-09T18-22-13.999999+00-00',  # _SUCCESS, _CLICKHOUSE_LOAD_SUCCESS
        ]
        for reference_genome, dataset_type in [
            (ReferenceGenome.GRCh38, DatasetType.SNV_INDEL),
            (ReferenceGenome.GRCh37, DatasetType.SNV_INDEL),
            (ReferenceGenome.GRCh38, DatasetType.GCNV),
            (ReferenceGenome.GRCh37, DatasetType.GCNV),
        ]:
            for run_id in run_ids:
                base_path = runs_path(reference_genome, dataset_type)
                os.makedirs(os.path.join(base_path, run_id), exist_ok=True)
                if '07T12' in run_id:
                    failure_file = clickhouse_load_fail_file_path(
                        reference_genome,
                        dataset_type,
                        run_id,
                    )
                    open(failure_file, 'w').close()
                if '09' in run_id or '07T12' in run_id:
                    success_file = pipeline_run_success_file_path(
                        reference_genome,
                        dataset_type,
                        run_id,
                    )
                    open(success_file, 'w').close()
                if '09T18' in run_id:
                    success_file = clickhouse_load_success_file_path(
                        reference_genome,
                        dataset_type,
                        run_id,
                    )
                    open(success_file, 'w').close()

    def test_get_run_ids(self) -> None:
        (
            successful_pipeline_runs,
            successful_clickhouse_loads,
            failed_clickhouse_loads,
        ) = get_run_ids()
        self.assertCountEqual(
            successful_pipeline_runs[(ReferenceGenome.GRCh38, DatasetType.SNV_INDEL)],
            {
                'manual__2024-08-09T18-22-13.999999+00-00',
                'manual__2024-08-08T09-45-00.000000+00-00',
                'manual__2024-08-07T12-30-45.654321+00-00',
            },
        )
        self.assertCountEqual(
            successful_clickhouse_loads[
                (ReferenceGenome.GRCh38, DatasetType.SNV_INDEL)
            ],
            {
                'manual__2024-08-09T18-22-13.999999+00-00',
            },
        )
        self.assertCountEqual(
            successful_clickhouse_loads[(ReferenceGenome.GRCh37, DatasetType.GCNV)],
            {},
        )
        self.assertCountEqual(
            failed_clickhouse_loads[(ReferenceGenome.GRCh38, DatasetType.SNV_INDEL)],
            {'manual__2024-08-07T12-30-45.654321+00-00'},
        )
