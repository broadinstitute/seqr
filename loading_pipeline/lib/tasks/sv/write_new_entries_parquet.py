import json

import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.misc.family_entries import (
    compute_callset_family_entries_ht,
)
from loading_pipeline.lib.misc.io import import_vcf
from loading_pipeline.lib.paths import (
    new_entries_parquet_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet_from_vcf import (
    BaseWriteParquetFromVcfTask,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.sv.write_deduplicated_vcf import (
    WriteDeduplicatedSvVcfTask,
)
from loading_pipeline.lib.tasks.sv.write_metadata_for_run import (
    WriteMetadataForSvRunTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewSvEntriesParquetTask(BaseWriteParquetFromVcfTask):
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
            self.clone(WriteDeduplicatedSvVcfTask),
            self.clone(WriteMetadataForSvRunTask),
        ]

    def create_table(self) -> hl.Table:
        existing_id_target = luigi.LocalTarget(is_tmp=True)
        existing_id_target.path += '.vcf.gz'
        self.run_bcftools(
            ['view', '-G', '-i', 'GT[0]="alt" && INFO/MatchId!="."'],
            existing_id_target,
            self.input()[0][:1],
        )
        id_map_ht = import_vcf(existing_id_target.path, self.reference_genome).rows()
        id_map_ht = id_map_ht.key_by(match_id=id_map_ht.info.MatchId[0]).select('rsid')

        matched_target = luigi.LocalTarget(is_tmp=True)
        matched_target.path += '.vcf.gz'
        self.run_bcftools(
            ['view', '-i', 'GT[1-]="alt" && INFO/MatchId!="."'],
            matched_target,
            self.input()[0][:1],
        )
        filter_map_ht = import_vcf(
            existing_id_target.path,
            self.reference_genome,
        ).rows()
        filter_map = filter_map_ht.group_by(filter_map_ht.info.MatchId[0]).aggregate(
            filters=hl.set(hl.flatten(hl.agg.collect(filter_map_ht.filters))),
        )

        collapsed_target = luigi.LocalTarget(is_tmp=True)
        collapsed_target.path += '.vcf.gz'
        self.run_bcftools(
            ['view', '-i', 'INFO/MatchId="."'],
            collapsed_target,
            self.input()[0][:1],
        )

        mt = import_vcf(collapsed_target.path, self.reference_genome)
        mt = mt.filter_cols(mt.s != 'seqr_existing')
        mt = mt.annotate_cols(GT=hl.or_else(mt.GT, [0, 0]))
        mt.annotate_rows(
            filters=mt.filters.union(filter_map[mt.info.CollapseId].filters),
        )
        mt = mt.key_rows_by(
            variant_id=hl.or_else(
                id_map_ht[mt.info.CollapseId].rsid,
                mt.rsid,
            ),
        )

        with self.input()[1].open() as f:
            metadata_json = json.load(f)
        mt = mt.annotate_globals(
            family_samples=metadata_json['family_samples'],
            project_families=metadata_json['project_families'],
        )

        ht = compute_callset_family_entries_ht(
            self.dataset_type,
            mt,
            {
                name: fn(mt, **self.param_kwargs)
                for name, fn in self.dataset_type.genotype_entry_annotation_fns.items()
            },
            self.sample_type,
        )

        # the family entries ht will contain rows
        # where at least one family is defined... after explosion,
        # rows where a family is not defined should be removed.
        ht = ht.explode(ht.family_entries)
        ht = ht.filter(hl.is_defined(ht.family_entries))
        ht = ht.select_globals()
        return ht.transmute(**ht.family_entries)
