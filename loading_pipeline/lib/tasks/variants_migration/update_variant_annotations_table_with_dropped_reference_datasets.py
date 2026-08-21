import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.paths import (
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.base.base_update import (
    BaseUpdateTask,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget, HailTableTask


@luigi.util.inherits(BaseLoadingPipelineParams)
class UpdateVariantAnnotationsTableWithDroppedReferenceDatasetsTask(
    BaseUpdateTask,
):
    run_id = luigi.Parameter()

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            variant_annotations_table_path(
                self.reference_genome,
                self.dataset_type,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        return HailTableTask(
            variant_annotations_table_path(
                self.reference_genome,
                self.dataset_type,
            ),
        )

    def complete(self) -> bool:
        return (
            super().complete() and 'dbnsfp' not in hl.read_table(self.output().path).row
        )

    def initialize_table(self) -> hl.Table:
        key_type = self.dataset_type.table_key_type(self.reference_genome)
        return hl.Table.parallelize(
            [],
            key_type,
            key=key_type.fields,
            globals=hl.Struct(
                enums=hl.Struct(),
                updates=hl.empty_set(
                    hl.tstruct(
                        callset=hl.tstr,
                        project_guid=hl.tstr,
                        remap_pedigree_hash=hl.tint32,
                    ),
                ),
                migrations=hl.empty_array(hl.tstr),
                max_key_=hl.int64(-1),
            ),
        )

    def update_table(self, ht: hl.Table) -> hl.Table:
        for field in [
            'clinvar',
            'gnomad_mito',
            'hmtvar',
            'local_constraint_mito',
            'dbnsfp',
            'mitomap',
            'mitimpact',
            'helix_mito',
            'gt_stats',
            'high_constraint_region',
            'eigen',
            'splice_ai',
            'exac',
            'topmed',
            'screen',
            'gnomad_exomes',
            'gnomad_genomes',
            'hgmd',
            'gnomad_non_coding_constraint',
        ]:
            if field in ht.row:
                ht = ht.drop(field)
            if field in ht.enums:
                ht = ht.annotate_globals(enums=ht.enums.drop(field))
        return ht
