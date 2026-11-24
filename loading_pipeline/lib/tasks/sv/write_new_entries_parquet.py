import json

import luigi
import luigi.util
import pandas as pd
from pyliftover import LiftOver

from loading_pipeline.lib.core import ReferenceGenome
from loading_pipeline.lib.paths import (
    new_entries_parquet_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet_from_vcf import (
    BaseWriteParquetFromVcfTask,
)
from loading_pipeline.lib.tasks.sv.write_deduplicated_vcf import (
    WriteDeduplicatedSvVcfTask,
)
from loading_pipeline.lib.tasks.sv.write_metadata_for_run import (
    WriteMetadataForSvRunTask,
)

CONTIGS_37 = list(ReferenceGenome.GRCh37.contig_recoding().values())
INFO_ENTRY_FIELDS = {
    'pos': 'POS',
    'end': 'END',
    'qs': 'QUAL',
}


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewSvEntriesParquetTask(BaseWriteParquetFromVcfTask):
    def output_dir(self) -> str:
        return new_entries_parquet_path(
            self.reference_genome,
            self.dataset_type,
            self.run_id,
        )

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteDeduplicatedSvVcfTask),
            self.clone(WriteMetadataForSvRunTask),
        ]

    def create_data_frame(self) -> pd.DataFrame:
        matched_target = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(
            ['view', '-i', 'GT[1-]="alt"'],
            matched_target,
            self.input()[0][:1],
            output_type='v',
        )
        df = self.import_vcf(matched_target)
        if 'CHR2' in df:
            df['CHR2'] = df['CHR2'].mask(df['SVTYPE'] == 'INS')
        else:
            df['CHR2'] = None
        if 'END2' in df:
            df['END'] = df['END2'].fillna(df['END'])

        existing_id_target = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(
            ['view', '-G', '-i', 'GT[0]="alt" && INFO/MatchId!="."'],
            existing_id_target,
            self.input()[0][:1],
            output_type='v',
        )
        id_map_df = self.import_vcf(existing_id_target)
        id_map = (
            {}
            if id_map_df.empty
            else id_map_df.set_index(['MatchId', 'TRUVARI_FILTER'])['ID'].to_dict()
        )
        id_map = (
            df[df['CollapseId'].notna()]
            .set_index(['CollapseId', 'TRUVARI_FILTER'])['ID']
            .to_dict()
            | id_map
        )

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
        df['sample_pos'] = df['sample'].str.get('pos')
        df['sample_end'] = df['sample'].str.get('end')
        df['variantId'] = (
            df[['CollapseId', 'TRUVARI_FILTER']]
            .apply(tuple, axis=1)
            .map(id_map)
            .fillna(df[['MatchId', 'TRUVARI_FILTER']].apply(tuple, axis=1).map(id_map))
            .fillna(df['ID'])
        )

        df = df.groupby(['variantId', 'family_guid'], as_index=False).agg(
            filters=(
                'FILTER',
                lambda values: sorted(set().union(*values.str.split(';')) - {'PASS'}),
            ),
            calls=('sample', list),
            chrom=('#CHROM', 'first'),
            end_chrom=('CHR2', 'first'),
            pos=('sample_pos', 'min'),
            end=('sample_end', 'max'),
        )
        df['project_guid'] = df['family_guid'].map(family_guid_to_project_guid)
        df['sign'] = 1
        df['sample_type'] = self.sample_type.value

        # Run liftover
        lo = LiftOver('loading_pipeline/var/liftover/grch38_to_grch37.over.chain.gz')
        df['end_chrom'] = df['end_chrom'].fillna(df['chrom'])
        df[['liftedOverChrom', 'liftedOverPos']] = self._liftover(
            lo,
            df['chrom'],
            df['pos'],
        )
        df['liftedOverEnd'] = [
            pos if chrom else None
            for chrom, pos in self._liftover(lo, df['end_chrom'], df['end'])
        ]
        df['xposEnd'] = self._xpos(df.pop('end_chrom'), df.pop('end'))
        df['xpos'] = self._xpos(df.pop('chrom'), df.pop('pos'))

        # Add ref calls for missing family members
        df['calls'] = df.apply(
            lambda row: sorted(
                row['calls']
                + [
                    {**dict.fromkeys(row['calls'][0]), 'sampleId': s, 'gt': 0}
                    for s in metadata_json['family_samples'][row['family_guid']]
                    if s not in {c['sampleId'] for c in row['calls']}
                ],
                key=lambda c: c['sampleId'],
            ),
            axis=1,
        )

        return df

    @classmethod
    def _parsed_sample_df(cls, df: pd.DataFrame, sample_ids: list[str]) -> pd.DataFrame:
        df['samples'] = df.apply(
            lambda row: [
                {
                    'sampleId': s,
                    **{k: row[field] for k, field in INFO_ENTRY_FIELDS.items()},
                    **dict(
                        zip(
                            row['FORMAT'].lower().split(':'),
                            row[s].split(':'),
                            strict=True,
                        ),
                    ),
                }
                for s in sample_ids
            ],
            axis=1,
        )
        df['samples'] = df['samples'].map(
            lambda samples: [s for s in samples if '1' in s['gt']],
        )

        matched_samples = df.groupby(['MatchId', 'TRUVARI_FILTER'])['samples'].agg(
            lambda rows: {s['sampleId'] for samples in rows for s in samples},
        )
        df['sample'] = df.apply(
            lambda row: next(
                (
                    dict([cls._format_sample_field(*i) for i in s.items()])
                    for s in row['samples']
                    if s['sampleId']
                    not in matched_samples.get(
                        (row['CollapseId'], row['TRUVARI_FILTER']),
                        set(),
                    )
                ),
                None,
            ),
            axis=1,
        )
        df = df[df['sample'].notna()]

        return df.drop(columns=[*sample_ids, 'seqr_existing', 'samples'])

    @staticmethod
    def _format_sample_field(field, value):
        if field == 'sampleId':
            return field, value
        if field == 'rd_cn':
            field = 'cn'
        if value is None:
            return field, None
        if field == 'gt':
            return field, sum(map(int, value.split('/')))
        return field, int(value)

    @classmethod
    def _liftover(cls, lo, df_chrom, df_pos):
        return [
            cls._liftover_coords(lo, c, p)
            for c, p in zip(df_chrom, df_pos, strict=False)
        ]

    @staticmethod
    def _liftover_coords(lo, chrom, pos):
        result = lo.convert_coordinate(chrom, pos - 1)
        if result and result[0][0] not in CONTIGS_37:
            result = None
        return (result[0][0], result[0][1] + 1) if result else (None, None)

    @staticmethod
    def _xpos(chrom, pos):
        return (
            chrom.str.removeprefix('chr').replace({'X': '23', 'Y': '24'}).astype(int)
            * 1_000_000_000
            + pos
        )
