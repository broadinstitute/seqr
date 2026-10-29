import json

import luigi
import luigi.util
import pandas as pd

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
            ['view', '-G', '-i', 'GT[0]="alt" && INFO/MatchId!="."'],
            existing_id_target,
            self.input()[0][:1],
            output_type='v',
        )
        id_map_df = self.import_vcf(existing_id_target)
        id_map = {} if id_map_df.empty else id_map_df.set_index(['MatchId', 'SVTYPE'])['ID'].to_dict()

        matched_target = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(
            ['view','-i', 'GT[1-]="alt"'],
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

        df = self._parsed_sample_df(df, list(sample_id_to_family_guid.keys()))
        df['family_guid'] = df['sample'].str['sampleId'].map(sample_id_to_family_guid)

        id_map = df[df['CollapseId'].notna()].set_index(['CollapseId', 'SVTYPE'])['ID'].to_dict() | id_map
        df['variantId'] = (
            df[['CollapseId', 'SVTYPE']].apply(tuple, axis=1).map(id_map)
            .fillna(df[['MatchId', 'SVTYPE']].apply(tuple, axis=1).map(id_map))
            .fillna(df['ID'])
        )

        df = df.groupby(['variantId', 'family_guid'], as_index=False).agg(
            filters=('FILTER', lambda values: set().union(*values.str.split(';'))),
            calls=('sample', list),
        )
        df['project_guid'] = df['family_guid'].map(family_guid_to_project_guid)
        df['sign'] = 1

        # cn: RD_CN
        # gq: hl.if_else(is_called, mt.GQ, 0)
        # gt: mt.GT.n_alt_alleles()
        return df

    @staticmethod
    def _parsed_sample_df(df: pd.DataFrame, sample_ids: list[str]) -> pd.DataFrame:
        df['samples'] = df.apply(
            lambda row: [
                {'sampleId': s, **dict(zip(row['FORMAT'].split(':'), row[s].split(':')))}
                for s in sample_ids
            ],
            axis=1,
        )
        df['samples'] = df['samples'].map(lambda samples: [s for s in samples if '1' in s['GT']])

        matched_samples = df.groupby(df['MatchId'])['samples'].agg(
            lambda rows: {s['sampleId'] for samples in rows for s in samples},
        )
        df['sample'] = df.apply(
            lambda row: next(
                (
                    s for s in row['samples']
                    if s['sampleId'] not in matched_samples.get(row['CollapseId'], set())
                ),
                None,
            ),
            axis=1,
        )
        df = df[df['sample'].notna()]

        return df.drop(columns=[*sample_ids, 'seqr_existing', 'samples'])
