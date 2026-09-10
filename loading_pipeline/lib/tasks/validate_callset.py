import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.misc.validation import (
    ALL_VALIDATIONS,
    SKIPPABLE_VALIDATIONS,
    SeqrValidationError,
)
from loading_pipeline.lib.paths import (
    postprocessed_callset_path,
    valid_reference_dataset_path,
)
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_update import BaseUpdateTask
from loading_pipeline.lib.tasks.files import CallsetTask, GCSorLocalTarget
from loading_pipeline.lib.tasks.reference_data.updated_reference_dataset import (
    UpdatedReferenceDatasetTask,
)
from loading_pipeline.lib.tasks.write_postprocessed_callset import (
    WritePostprocessedCallsetTask,
)
from loading_pipeline.lib.tasks.write_validation_errors_for_run import (
    UpdatedValidationErrorsForRunTask,
)

MAX_SNV_INDEL_ALLELE_LENGTH = 500


@luigi.util.inherits(BaseLoadingRunParams)
class ValidateCallsetTask(BaseUpdateTask):
    @property
    def validation_dependencies(self) -> dict[str, hl.Table]:
        deps = {}
        if (
            ALL_VALIDATIONS not in self.validations_to_skip
            and 'validate_sample_type' not in self.validations_to_skip
            and self.dataset_type.can_run_validation
        ):
            deps['coding_and_noncoding_variants_ht'] = hl.read_table(
                valid_reference_dataset_path(
                    self.reference_genome,
                    ReferenceDataset.gnomad_coding_and_noncoding,
                ),
            )
        return deps

    def complete(self) -> luigi.Target:
        if super().complete():
            mt = hl.read_matrix_table(self.output().path)
            return hasattr(mt, 'validated_sample_type') and hl.eval(
                self.sample_type.value == mt.validated_sample_type,
            )
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
        requirements = [self.clone(WritePostprocessedCallsetTask)]
        if (
            ALL_VALIDATIONS not in self.validations_to_skip
            and 'validate_sample_type' not in self.validations_to_skip
            and self.dataset_type.can_run_validation
        ):
            requirements = [
                *requirements,
                (
                    self.clone(
                        UpdatedReferenceDatasetTask,
                        reference_dataset=ReferenceDataset.gnomad_coding_and_noncoding,
                    )
                ),
            ]
        return [
            *requirements,
            CallsetTask(self.callset_path),
        ]

    def update_table(self, mt: hl.MatrixTable) -> hl.MatrixTable:
        mt = hl.read_matrix_table(
            postprocessed_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )
        if self.dataset_type.filter_invalid_sites:
            mt = mt.filter_rows(
                (
                    # Rather than throwing an error, we silently remove invalid contigs.
                    # This happens fairly often for AnVIL requests.
                    hl.set(self.reference_genome.standard_contigs).contains(
                        mt.locus.contig,
                    )
                    # DRAGEN callsets produce long alternate alleles
                    # that aren't particularly analyzable as INDELs.
                    & (hl.len(mt.alleles[1]) < MAX_SNV_INDEL_ALLELE_LENGTH)
                ),
            )

        if (
            ALL_VALIDATIONS in self.validations_to_skip
            or not self.dataset_type.can_run_validation
        ):
            return mt.select_globals(
                callset_path=self.callset_path,
                validated_sample_type=self.sample_type.value,
            )
        validation_exceptions = []
        for validation_f in SKIPPABLE_VALIDATIONS:
            try:
                if validation_f.__name__ in self.validations_to_skip:
                    continue
                validation_f(
                    mt,
                    **self.validation_dependencies,
                    **self.param_kwargs,
                )
            except SeqrValidationError as e:
                validation_exceptions.append(e)
        if validation_exceptions:
            updated_validation_errors_for_run_task = self.clone(
                UpdatedValidationErrorsForRunTask,
                error_messages=[e.msg for e in validation_exceptions],
                error_body={
                    k: v for e in validation_exceptions for k, v in e.error_body.items()
                },
            )
            updated_validation_errors_for_run_task.run()
            raise SeqrValidationError(
                updated_validation_errors_for_run_task.to_single_error_message(),
            )
        return mt.select_globals(
            callset_path=self.callset_path,
            validated_sample_type=self.sample_type.value,
        )
