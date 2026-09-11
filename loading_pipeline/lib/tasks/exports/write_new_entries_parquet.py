import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.annotations.fields import get_fields
from loading_pipeline.lib.misc.family_entries import (
    compute_callset_family_entries_ht,
    deduplicate_by_most_non_ref_calls,
    deglobalize_ids,
)
from loading_pipeline.lib.paths import (
    new_entries_parquet_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet import BaseWriteParquetTask
from loading_pipeline.lib.tasks.exports.fields import (
    get_entries_export_fields,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
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

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteRemappedAndSubsettedCallsetTask),
        ]

    def create_table(self) -> hl.Table:
        mt = hl.read_matrix_table(self.input()[0].path)
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

        # the family entries ht will contain rows
        # where at least one family is defined... after explosion,
        # rows where a family is not defined should be removed.
        ht = ht.explode(ht.family_entries)
        ht = ht.filter(hl.is_defined(ht.family_entries))
        ht = ht.key_by()
        ht = ht.select_globals()
        return ht.select(
            **get_entries_export_fields(
                ht,
                self.dataset_type,
                self.sample_type,
            ),
        )
