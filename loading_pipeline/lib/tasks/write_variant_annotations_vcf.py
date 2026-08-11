import hail as hl
import hailtop.fs as hfs
import luigi

from loading_pipeline.lib.annotations.fields import get_fields
from loading_pipeline.lib.paths import (
    variant_annotations_table_path,
    variant_annotations_vcf_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.files import GCSorLocalTarget


@luigi.util.inherits(BaseLoadingRunParams)
class WriteVariantAnnotationsVCF(luigi.Task):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            variant_annotations_vcf_path(
                self.reference_genome,
                self.dataset_type,
            ),
        )

    def complete(self) -> bool:
        return not self.dataset_type.should_export_to_vcf

    def run(self) -> None:
        if not hfs.exists(
            variant_annotations_table_path(
                self.reference_genome,
                self.dataset_type,
            ),
        ):
            return
        ht = hl.read_table(
            variant_annotations_table_path(
                self.reference_genome,
                self.dataset_type,
            ),
        )
        ht = ht.annotate(
            **get_fields(
                ht,
                self.dataset_type.export_vcf_annotation_fns,
                **self.param_kwargs,
            ),
        )
        ht = ht.key_by('locus', 'alleles')
        hl.export_vcf(ht, self.output().path, tabix=True)
