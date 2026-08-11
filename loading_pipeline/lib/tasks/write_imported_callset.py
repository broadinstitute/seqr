import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.misc.callsets import get_additional_row_fields
from loading_pipeline.lib.misc.io import (
    import_callset,
    select_relevant_fields,
)
from loading_pipeline.lib.misc.validation import (
    validate_imported_field_types,
)
from loading_pipeline.lib.paths import (
    imported_callset_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.files import CallsetTask, GCSorLocalTarget
from loading_pipeline.lib.tasks.write_validation_errors_for_run import (
    with_persisted_validation_errors,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteImportedCallsetTask(BaseWriteTask):
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
            imported_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        return [
            CallsetTask(self.callset_path),
        ]

    @with_persisted_validation_errors
    def create_table(self) -> hl.MatrixTable:
        # NB: throws SeqrValidationError
        mt = import_callset(
            self.callset_path,
            self.reference_genome,
            self.dataset_type,
        )
        additional_row_fields = get_additional_row_fields(
            mt,
            self.reference_genome,
            self.dataset_type,
            self.skip_check_sex_and_relatedness,
        )
        # NB: throws SeqrValidationError
        mt = select_relevant_fields(
            mt,
            self.dataset_type,
            additional_row_fields,
        )
        # This validation isn't override-able by the skip option.
        # If a field is the wrong type, the pipeline will likely hard-fail downstream.
        # NB: throws SeqrValidationError
        validate_imported_field_types(
            mt,
            self.dataset_type,
            additional_row_fields,
        )
        return mt.select_globals(
            callset_path=self.callset_path,
        )
