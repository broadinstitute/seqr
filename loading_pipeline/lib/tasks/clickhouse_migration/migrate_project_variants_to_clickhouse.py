import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.core import SampleType
from loading_pipeline.lib.paths import (
    new_variants_table_path,
    project_table_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.exports.write_new_variant_details_parquet import (
    WriteNewVariantDetailsParquetTask,
)
from loading_pipeline.lib.tasks.exports.write_new_variants_parquet import (
    WriteNewVariantsParquetTask,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget, HailTableTask

MAX_SNV_INDEL_ALLELE_LENGTH = 500


class WriteProjectSubsettedVariantsTask(BaseWriteTask):
    run_id = luigi.Parameter()
    sample_type = luigi.EnumParameter(enum=SampleType)
    project_guid = luigi.Parameter()

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            new_variants_table_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        return [
            HailTableTask(
                variant_annotations_table_path(
                    self.reference_genome,
                    self.dataset_type,
                ),
            ),
            HailTableTask(
                project_table_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.sample_type,
                    self.project_guid,
                ),
            ),
        ]

    def create_table(self) -> hl.Table:
        ht = hl.read_table(self.input()[0].path)
        if not hasattr(ht, 'key_'):
            ht = ht.add_index(name='key_')
        if self.dataset_type.filter_invalid_sites:
            ht = ht.filter(hl.len(ht.alleles[1]) < MAX_SNV_INDEL_ALLELE_LENGTH)
        project_ht = hl.read_table(self.input()[1].path)
        return ht.semi_join(project_ht)


@luigi.util.inherits(BaseLoadingPipelineParams)
class MigrateProjectVariantsToClickHouseTask(luigi.WrapperTask):
    run_id = luigi.Parameter()
    sample_type = luigi.EnumParameter(enum=SampleType)
    project_guid = luigi.Parameter()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dynamic_parquet_tasks = set()

    def requires(self) -> luigi.Task:
        return self.clone(WriteProjectSubsettedVariantsTask)

    def complete(self):
        return (
            super().complete()
            and len(self.dynamic_parquet_tasks) >= 1
            and all(
                dynamic_parquet_tasks.complete()
                for dynamic_parquet_tasks in self.dynamic_parquet_tasks
            )
        )

    def run(self):
        self.dynamic_parquet_tasks.update(
            [
                *(
                    [
                        self.clone(
                            WriteNewVariantDetailsParquetTask,
                            # Callset Path being required
                            # here is byproduct of the "place all variants"
                            # in the variants path" hack.  In theory
                            # it is possible to re-factor the parameters
                            # such that this isn't required, but it's left
                            # as out of scope for now.  Alternatively,
                            # we could inherit the functionality of these
                            # tasks without calling them directly, but
                            # that was also more code.
                            callset_path=None,
                        ),
                    ]
                    if self.dataset_type.should_write_new_variant_details
                    else []
                ),
                self.clone(
                    WriteNewVariantsParquetTask,
                    callset_path=None,
                ),
            ],
        )
        yield self.dynamic_parquet_tasks
