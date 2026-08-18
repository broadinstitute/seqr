import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.annotations.fields import get_fields
from loading_pipeline.lib.misc.callsets import get_callset_ht
from loading_pipeline.lib.misc.io import remap_pedigree_hash
from loading_pipeline.lib.paths import (
    new_variants_table_path,
    project_pedigree_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_update import (
    BaseUpdateTask,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_new_variants_table import (
    WriteNewVariantsTableTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class UpdateVariantAnnotationsTableWithNewVariantsTask(
    BaseUpdateTask,
):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            variant_annotations_table_path(
                self.reference_genome,
                self.dataset_type,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        return [
            *super().requires(),
            self.clone(WriteNewVariantsTableTask),
        ]

    def complete(self) -> bool:
        return super().complete() and hl.eval(
            hl.bind(
                lambda updates: hl.all(
                    [
                        updates.contains(
                            hl.Struct(
                                callset=self.callset_path,
                                project_guid=project_guid,
                                remap_pedigree_hash=remap_pedigree_hash(
                                    project_pedigree_path(
                                        self.reference_genome,
                                        self.dataset_type,
                                        self.sample_type,
                                        project_guid,
                                    ),
                                ),
                            ),
                        )
                        for project_guid in self.project_guids
                    ],
                ),
                hl.read_table(self.output().path).updates,
            ),
        )

    def initialize_table(self) -> hl.Table:
        key_type = self.dataset_type.table_key_type(self.reference_genome)
        return hl.Table.parallelize(
            [],
            key_type,
            key=key_type.fields,
            globals=hl.Struct(
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
        # Gracefully handle case for on-premises uses
        # where key_ field is not present and migration was not run.
        if not hasattr(ht, 'key_'):
            ht = ht.add_index(name='key_')
            ht = ht.annotate_globals(max_key_=(ht.count() - 1))

        new_variants_ht = hl.read_table(
            new_variants_table_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

        # Union with the new variants table and annotate with the lookup table.
        ht = ht.union(new_variants_ht, unify=True)

        if self.dataset_type.variant_frequency_annotation_fns:
            # new_variants_ht consists of variants present in the new callset, fully annotated,
            # but NOT present in the existing annotations table.
            # callset_variants_ht consists of variants present in the new callset, fully annotated,
            # and either present or not present in the existing annotations table.
            callset_ht = get_callset_ht(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
                self.project_guids,
            )
            callset_variants_ht = ht.semi_join(callset_ht)
            non_callset_variants_ht = ht.anti_join(callset_ht)
            callset_variants_ht = callset_variants_ht.annotate(
                **get_fields(
                    callset_variants_ht,
                    self.dataset_type.variant_frequency_annotation_fns,
                    callset_ht=callset_ht,
                    **self.param_kwargs,
                ),
            )
            ht = non_callset_variants_ht.union(callset_variants_ht, unify=True)

        new_variants_ht_globals = new_variants_ht.index_globals()
        return ht.select_globals(
            updates=ht.updates.union(new_variants_ht_globals.updates),
            migrations=ht.migrations,
            max_key_=ht.aggregate(hl.agg.max(ht.key_)),
        )
