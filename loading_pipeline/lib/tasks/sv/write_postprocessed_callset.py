import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.misc.io import (
    import_parquet,
)
from loading_pipeline.lib.misc.sv import deduplicate_merged_sv_concordance_calls
from loading_pipeline.lib.paths import (
    existing_variants_parquet_path,
    imported_callset_path,
    postprocessed_callset_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.sv.write_imported_callset import (
    WriteImportedSvCallsetTask,
)
from loading_pipeline.lib.tasks.write_existing_variants_parquet import (
    WriteExistingVariantsParquetTask,
)
from loading_pipeline.lib.tasks.write_validation_errors_for_run import (
    with_persisted_validation_errors,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WritePostprocessedSvCallsetTask(BaseWriteTask):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            postprocessed_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteImportedSvCallsetTask),
            self.clone(WriteExistingVariantsParquetTask),
        ]

    @with_persisted_validation_errors
    def create_table(self) -> hl.MatrixTable:
        mt = hl.read_matrix_table(
            imported_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )
        mt = deduplicate_merged_sv_concordance_calls(
            mt,
            import_parquet(
                existing_variants_parquet_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.run_id,
                ),
                self.reference_genome,
                self.dataset_type,
            ),
        )
        mt = mt.key_rows_by(
            variant_id=hl.if_else(
                hl.is_defined(mt['info.SEQR_INTERNAL_TRUTH_VID']),
                mt['info.SEQR_INTERNAL_TRUTH_VID'],
                mt.variant_id,
            ),
        )

        return mt.select_globals(
            callset_path=self.callset_path,
        )
