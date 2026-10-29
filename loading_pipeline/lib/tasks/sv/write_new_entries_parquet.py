import json

import luigi
import luigi.util
import pandas as pd

from loading_pipeline.lib.misc.family_entries import (
    compute_callset_family_entries_ht,
)
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

    def create_data_frame(self) -> pd.DataFrame:
        existing_id_target = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(
            ['view', '-GH', '-i', 'GT[0]="alt" && INFO/MatchId!="."'],
            existing_id_target,
            self.input()[0][:1],
            output_type='v',
        )
        id_map_df = self.import_vcf(existing_id_target)
        id_map_df['match_id'] = id_map_df['INFO'].str['MatchId']
        id_map = id_map_df.set_index('match_id')['ID']

        matched_target = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(
            ['view', '-H', '-i', 'GT[1-]="alt"'],
            matched_target,
            self.input()[0][:1],
            output_type='v',
        )
        df = self.import_vcf(matched_target)

        with self.input()[1].open() as f:
            metadata_json = json.load(f)
        sample_id_to_family_guid = {
            s: family_guid
            for family_guid, sample_ids in metadata_json['family_samples'].items()
            for s in sample_ids
        }
        family_guid_to_project_guid = {
            family_guid: project_guid
            for project_guid, family_guids in metadata_json['project_families'].items()
            for family_guid in family_guids
        }

        df = self._parsed_sample_df(df)
        df['family_guid'] = df['sample'].str['sampleId'].map(sample_id_to_family_guid)
        df['variantId'] = (
            df['INFO'].str['CollapseId'].map(id_map)
            .fillna(df['INFO'].str['MatchId'].map(id_map))
            .fillna(df['ID'])
        )

        df = df.groupby(['variantId', 'family_guid']).agg(
            filters=('FILTER', lambda values: set().union(*values.str.split(';'))),
            calls=('sample', list),
        )
        df['project_guid'] = df['family_guid'].map(family_guid_to_project_guid)

        # mt = mt.annotate_entries(GT=hl.or_else(mt.GT, hl.call(0, 0)))
        #
        # ht = compute_callset_family_entries_ht(
        #     self.dataset_type,
        #     mt,
        #     {
        #         name: fn(mt, **self.param_kwargs)
        #         for name, fn in self.dataset_type.genotype_entry_annotation_fns.items()
        #     },
        #     self.sample_type,
        # )

        return df

    @staticmethod
    def _parsed_sample_df(df: pd.DataFrame) -> pd.DataFrame:
        sample_cols = df.columns[df.columns.get_loc('seqr_existing') + 1:]
        df['samples'] = df.apply(
            lambda row: [
                {'sampleId': s, **dict(zip(row['FORMAT'].split(':'), row[s].split(':')))}
                for s in sample_cols
            ],
            axis=1,
        )
        df['samples'] = df['samples'].map(lambda samples: [s for s in samples if '1' in s['GT']])

        matched_samples = df.groupby(df['INFO'].str['MatchId'])['samples'].agg(
            lambda rows: {s['sampleId'] for samples in rows for s in samples},
        )
        df['sample'] = df.apply(
            lambda row: next(
                s for s in row['samples']
                if s['sampleId'] not in matched_samples.get(row['INFO'].get('CollapseId'), set())
            ),
            axis=1,
        )

        return df.drop(columns=[*sample_cols, 'seqr_existing', 'samples'])
