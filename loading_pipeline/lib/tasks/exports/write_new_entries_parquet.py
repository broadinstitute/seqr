import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.annotations.fields import get_fields
from loading_pipeline.lib.annotations.shared import xpos
from loading_pipeline.lib.misc.family_entries import (
    compute_callset_family_entries_ht,
    deduplicate_by_most_non_ref_calls,
    deglobalize_ids,
)
from loading_pipeline.lib.misc.io import import_parquet
from loading_pipeline.lib.paths import (
    new_entries_parquet_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet import BaseWriteParquetTask
from loading_pipeline.lib.tasks.exports.fields import (
    get_entries_annotations_export_fields,
    get_entries_call_annotations_fields,
    get_entries_export_fields,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_existing_variants_parquet import (
    WriteExistingVariantsParquetTask,
)
from loading_pipeline.lib.tasks.write_new_variants_table import (
    WriteNewVariantsTableTask,
)
from loading_pipeline.lib.tasks.write_remapped_and_subsetted_callset import (
    WriteRemappedAndSubsettedCallsetTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewEntriesParquetTask(BaseWriteParquetTask):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            new_entries_parquet_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> dict[str, luigi.Task]:
        return [
            self.clone(WriteExistingVariantsParquetTask),
            self.clone(WriteNewVariantsTableTask),
            self.clone(WriteRemappedAndSubsettedCallsetTask),
        ]

    def create_table(self) -> None:
        annotations_ht = hl.read_table(self.input()[1].path)
        annotation_selects = {
            field: func(annotations_ht)
            for field, func in {
                **get_entries_annotations_export_fields(self.dataset_type),
                **get_entries_call_annotations_fields(self.dataset_type),
            }.items()
        }
        annotations_ht = annotations_ht.select(**annotation_selects)

        existing_annotations_ht = import_parquet(
            self.input()[0].path,
            self.reference_genome,
            self.dataset_type,
        )
        if 'xpos' not in existing_annotations_ht.row:
            existing_annotations_ht = existing_annotations_ht.annotate(
                xpos=hl.int64(xpos(existing_annotations_ht)),
            )
        if 'gene_ids' in existing_annotations_ht.row:
            existing_annotations_ht = existing_annotations_ht.annotate(
                gene_ids=hl.set(existing_annotations_ht.gene_ids),
            )
        if 'geneIds' in existing_annotations_ht.row:
            existing_annotations_ht = existing_annotations_ht.annotate(
                geneIds=hl.set(existing_annotations_ht.geneIds),
            )

        annotations_ht = annotations_ht.union(
            existing_annotations_ht.select(*annotation_selects),
        )

        for project_guid in self.project_guids:
            # TODO remove loop
            mt = hl.read_matrix_table(self.input()[2].path)
            ht = compute_callset_family_entries_ht(
                self.dataset_type,
                mt,
                get_fields(
                    mt,
                    self.dataset_type.genotype_entry_annotation_fns,
                    **self.param_kwargs,
                ),
            )
            ht = deglobalize_ids(ht)
            ht = deduplicate_by_most_non_ref_calls(ht)
            ht = ht.join(annotations_ht)

            # the family entries ht will contain rows
            # where at least one family is defined... after explosion,
            # rows where a family is not defined should be removed.
            ht = ht.explode(ht.family_entries)
            ht = ht.filter(hl.is_defined(ht.family_entries))
            ht = ht.key_by()
            ht = ht.select_globals()
            ht = ht.select(
                **get_entries_export_fields(
                    ht,
                    self.dataset_type,
                    self.sample_type,
                    project_guid,
                ),
            )
        return ht
