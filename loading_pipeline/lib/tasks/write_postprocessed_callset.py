import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.misc.callsets import get_additional_row_fields
from loading_pipeline.lib.misc.io import (
    split_multi_hts,
)
from loading_pipeline.lib.misc.sv import deduplicate_merged_sv_concordance_calls
from loading_pipeline.lib.misc.vets import annotate_vets
from loading_pipeline.lib.paths import (
    imported_callset_path,
    postprocessed_callset_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_imported_callset import WriteImportedCallsetTask
from loading_pipeline.lib.tasks.write_validation_errors_for_run import (
    with_persisted_validation_errors,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WritePostprocessedCallsetTask(BaseWriteTask):
    def complete(self) -> luigi.Target:
        if super().complete():
            mt = hl.read_matrix_table(self.output().path)
            # Handle case where callset was previously imported
            # with a different sex/relatedness flag.
            additional_row_fields = get_additional_row_fields(
                mt,
                self.reference_genome,
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
        return [self.clone(WriteImportedCallsetTask)]

    @with_persisted_validation_errors
    def create_table(self) -> hl.MatrixTable:
        mt = hl.read_matrix_table(
            imported_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )

        if self.dataset_type.has_multi_allelic_variants:
            # NB: throws SeqrValidationError
            mt = split_multi_hts(
                mt,
                'validate_no_duplicate_variants' in self.validations_to_skip,
            )
        if self.dataset_type.re_key_by_seqr_internal_truth_vid and hasattr(
            mt,
            'info.SEQR_INTERNAL_TRUTH_VID',
        ):
            mt = deduplicate_merged_sv_concordance_calls(
                mt,
                hl.read_table(
                    variant_annotations_table_path(
                        self.reference_genome,
                        self.dataset_type,
                    ),
                ),
            )
            mt = mt.key_rows_by(
                variant_id=hl.if_else(
                    hl.is_defined(mt['info.SEQR_INTERNAL_TRUTH_VID']),
                    mt['info.SEQR_INTERNAL_TRUTH_VID'],
                    mt.variant_id,
                ),
            )

        # Special handling of variant-level filter annotation for VETs filters.
        # The annotations are present on the sample-level FT field but are
        # expected upstream on "filters".
        mt = annotate_vets(mt)
        return mt.select_globals(
            callset_path=self.callset_path,
        )
