import json

import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.core import SampleType
from loading_pipeline.lib.misc.family_entries import (
    deduplicate_by_most_non_ref_calls,
    deglobalize_ids,
)
from loading_pipeline.lib.paths import (
    metadata_for_run_path,
    new_entries_parquet_path,
    pipeline_run_success_file_path,
    project_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet import BaseWriteParquetTask
from loading_pipeline.lib.tasks.clickhouse_migration.migrate_project_variants_to_clickhouse import (
    MigrateProjectVariantsToClickHouseTask,
    WriteProjectSubsettedVariantsTask,
)
from loading_pipeline.lib.tasks.exports.fields import get_entries_export_fields
from loading_pipeline.lib.tasks.files import GCSorLocalTarget, HailTableTask

PROJECT_SUBSETTED_ANNOTATIONS_TABLE_TASK = 'project_subsetted_annotations_table_task'
PROJECT_TABLE_TASK = 'project_table_task'


@luigi.util.inherits(BaseLoadingPipelineParams)
class WriteProjectEntriesParquetTask(BaseWriteParquetTask):
    run_id = luigi.Parameter()
    sample_type = luigi.EnumParameter(enum=SampleType)
    project_guid = luigi.Parameter()

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            new_entries_parquet_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        return {
            PROJECT_SUBSETTED_ANNOTATIONS_TABLE_TASK: self.clone(
                WriteProjectSubsettedVariantsTask,
            ),
            PROJECT_TABLE_TASK: HailTableTask(
                project_table_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.sample_type,
                    self.project_guid,
                ),
            ),
        }

    def create_table(self) -> None:
        ht = hl.read_table(
            self.input()[PROJECT_TABLE_TASK].path,
        )
        ht = deglobalize_ids(ht)
        ht = deduplicate_by_most_non_ref_calls(ht)
        annotations_ht = hl.read_table(
            self.input()[PROJECT_SUBSETTED_ANNOTATIONS_TABLE_TASK].path,
        )
        ht = ht.join(annotations_ht)
        ht = ht.explode(ht.family_entries)
        ht = ht.filter(hl.is_defined(ht.family_entries))
        ht = ht.key_by()
        ht = ht.select_globals()
        return ht.select(
            **get_entries_export_fields(
                ht,
                self.dataset_type,
                self.sample_type,
                self.project_guid,
            ),
        )


@luigi.util.inherits(BaseLoadingPipelineParams)
class WriteMigrationMetadataJsonTask(luigi.Task):
    run_id = luigi.Parameter()
    sample_type = luigi.EnumParameter(enum=SampleType)
    project_guid = luigi.Parameter()

    def requires(self):
        return HailTableTask(
            project_table_path(
                self.reference_genome,
                self.dataset_type,
                self.sample_type,
                self.project_guid,
            ),
        )

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            metadata_for_run_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def run(self):
        ht = hl.read_table(self.input().path)
        metadata_json = {
            'callsets': [],
            'run_id': self.run_id,
            'sample_type': self.sample_type.value,
            'project_guids': [self.project_guid],
            'family_samples': hl.eval(ht.globals.family_samples),
            'failed_family_samples': {
                'missing_samples': {},
                'relatedness_check': {},
                'sex_check': {},
                'ploidy_check': {},
            },
            'relatedness_check_file_path': '',
            'sample_qc': {},
        }
        with self.output().open('w') as f:
            json.dump(metadata_json, f)


@luigi.util.inherits(BaseLoadingPipelineParams)
class MigrateProjectToClickHouseTask(luigi.Task):
    run_id = luigi.Parameter()
    sample_type = luigi.EnumParameter(enum=SampleType)
    project_guid = luigi.Parameter()

    def requires(self):
        return [
            self.clone(MigrateProjectVariantsToClickHouseTask),
            self.clone(WriteProjectEntriesParquetTask),
            self.clone(WriteMigrationMetadataJsonTask),
        ]

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            pipeline_run_success_file_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def run(self):
        with self.output().open('w') as f:
            f.write('')
