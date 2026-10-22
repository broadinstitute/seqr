import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.misc.io import (
    import_callset,
)
from loading_pipeline.lib.misc.sv import (
    deduplicate_merged_sv_concordance_calls,
)
from loading_pipeline.lib.paths import (
    postprocessed_callset_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_vcf import BaseVCFTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.sv.write_combined_vcf import (
    WriteCombinedSvVcf,
)
from loading_pipeline.lib.tasks.sv.write_existing_variants_vcf import (
    WriteExistingVariantsVcfTask,
)
from loading_pipeline.lib.tasks.write_validation_errors_for_run import (
    with_persisted_validation_errors,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteDeduplicatedSvVcfTask(BaseVCFTask):
    def complete(self) -> bool:
        if not super().complete():
            return False

        # Ensure input VCF has the correct samples for the current run
        return self.requires()[0].complete()

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
            self.clone(WriteCombinedSvVcf),
            self.clone(WriteExistingVariantsVcfTask),
        ]

    @with_persisted_validation_errors
    def create_table(self) -> hl.MatrixTable:
        mt = import_callset(
            self.input()[0][0].remote_path or self.input()[0][0].path,
            self.reference_genome,
            self.dataset_type,
        )
        mt = mt.transmute_rows(**{f'info.{field}': mt.info[field] for field in mt.info})

        annotations_ht = import_callset(
            self.input()[1][0].remote_path or self.input()[1][0].path,
            self.reference_genome,
            self.dataset_type,
        ).rows()
        annotations_ht = annotations_ht.annotate(
            end=annotations_ht.info.END,
            endChrom=annotations_ht.info.CHR2,
        )
        annotations_ht = annotations_ht.key_by(variant_id=annotations_ht.rsid)

        mt = deduplicate_merged_sv_concordance_calls(
            mt,
            annotations_ht,
        )
        mt = mt.key_rows_by(
            variant_id=hl.if_else(
                hl.is_defined(mt['info.SEQR_INTERNAL_TRUTH_VID']),
                mt['info.SEQR_INTERNAL_TRUTH_VID'],
                mt.variant_id,
            ),
        )

        mt = mt.annotate_rows(is_new_variant=hl.is_missing(annotations_ht[mt.row_key]))

        self.input()[1][0].localize()
        with self.input()[1][0].open() as f:
            for line in f:
                if line.startswith('##maxKey'):
                    curr_max_key = int(line.split('##maxKey=')[1].strip())
                    break
                if not line.startswith('#'):
                    msg = 'Invalid VCF header'
                    raise RuntimeError(msg)

        return mt.select_globals(
            callset_path=self.callset_path,
            curr_max_key=curr_max_key,
        )
