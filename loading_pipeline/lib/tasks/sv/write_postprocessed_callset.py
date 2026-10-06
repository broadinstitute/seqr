import hail as hl
import json
import luigi
import luigi.util

from loading_pipeline.lib.misc.callsets import get_additional_row_fields
from loading_pipeline.lib.misc.io import (
    import_parquet,
)
from loading_pipeline.lib.misc.sv import deduplicate_merged_sv_concordance_calls, overwrite_male_non_par_calls
from loading_pipeline.lib.paths import (
    postprocessed_callset_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.sv.write_imported_callset import (
    WriteImportedSvCallsetTask,
)
from loading_pipeline.lib.tasks.sv.write_metadata_for_run import (
    WriteMetadataForSvRunTask,
)
from loading_pipeline.lib.tasks.write_existing_variants_parquet import (
    WriteExistingVariantsParquetTask,
)
from loading_pipeline.lib.tasks.write_validation_errors_for_run import (
    with_persisted_validation_errors,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WritePostprocessedSvCallsetTask(BaseWriteTask):
    def complete(self) -> luigi.Target:
        if super().complete():
            mt = hl.read_matrix_table(self.output().path)
            # Handle case where callset was previously imported
            # with a different sex/relatedness flag.
            additional_row_fields = get_additional_row_fields(
                mt,
                self.dataset_type,
                self.skip_check_sex_and_relatedness,
            )
            return all(hasattr(mt, field) for field in additional_row_fields)
        return False

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            postprocessed_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        requires = [self.clone(WriteImportedSvCallsetTask)]
        if self.dataset_type.re_key_by_seqr_internal_truth_vid:
            requires.append(self.clone(WriteExistingVariantsParquetTask))
        if self.dataset_type.overwrite_male_non_par_calls:
            requires.append(self.clone(WriteMetadataForSvRunTask))
        return requires

    @with_persisted_validation_errors
    def create_table(self) -> hl.MatrixTable:
        mt = hl.read_matrix_table(self.input()[0].path)

        if self.dataset_type.re_key_by_seqr_internal_truth_vid and hasattr(
            mt,
            'info.SEQR_INTERNAL_TRUTH_VID',
        ):
            mt = deduplicate_merged_sv_concordance_calls(
                mt,
                import_parquet(
                    self.input()[1].path,
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

        if self.dataset_type.overwrite_male_non_par_calls:
            with open(self.input()[-1].path) as f:
                metadata_json = json.load(f)
            mt = overwrite_male_non_par_calls(mt, metadata_json['male_sample_ids'])

        return mt.select_globals(
            callset_path=self.callset_path,
        )
