import json

import luigi
import luigi.util
import pandas as pd

from loading_pipeline.lib.annotations.enums import (
    SV_TYPE_DETAILS,
    SV_TYPES,
)
from loading_pipeline.lib.misc.sv import (
    annotate_gene_consequences,
    match_gnomad_af,
    run_strvctvre,
)
from loading_pipeline.lib.paths import (
    new_variants_parquet_path,
)
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet_from_vcf import (
    BaseWriteParquetFromVcfTask,
)
from loading_pipeline.lib.tasks.reference_data.updated_reference_dataset_parquet import (
    UpdatedReferenceDatasetParquetNoHailTask,
)
from loading_pipeline.lib.tasks.sv.write_deduplicated_vcf import (
    WriteDeduplicatedSvVcfTask,
)


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewSvVariantsParquetTask(BaseWriteParquetFromVcfTask):
    attempt_id = luigi.IntParameter()

    def output_dir(self) -> str:
        return new_variants_parquet_path(
            self.reference_genome,
            self.dataset_type,
            self.run_id,
        )

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteDeduplicatedSvVcfTask),
            self.clone(
                UpdatedReferenceDatasetParquetNoHailTask,
                reference_dataset=ReferenceDataset.gencode_transcripts,
                attempt_id=self.attempt_id,
            ),
            self.clone(
                UpdatedReferenceDatasetParquetNoHailTask,
                reference_dataset=ReferenceDataset.gnomad_svs,
                attempt_id=self.attempt_id,
            ),
            self.clone(
                UpdatedReferenceDatasetParquetNoHailTask,
                reference_dataset=ReferenceDataset.strvctre_phylop,
                attempt_id=self.attempt_id,
            ),
        ]

    def create_data_frame(self) -> pd.DataFrame:
        # Identify new variants.
        filtered_target = luigi.LocalTarget(is_tmp=True)
        self.run_bcftools(
            ['view', '-G', '-i', 'GT[0]="mis" && INFO/MatchId="."'],
            filtered_target,
            self.input()[0][:1],
            output_type='v',
        )
        df = self.import_vcf(filtered_target)
        original_columns = df.columns

        # Annotate gene consequences
        invalid_sv_types = df['SVTYPE'][~df['SVTYPE'].isin(SV_TYPES)]
        if not invalid_sv_types.empty:
            msg = f'Unexpected enum value: {invalid_sv_types.iloc[0]}'
            raise ValueError(msg)

        df.loc[df['SVTYPE'] == 'INS', 'sv_type_detail'] = df.pop('ALT').str.extract(
            r'^<[^:]+:(.+)>$',
        )[0]
        if 'CPX_TYPE' in df:
            df.loc[df['SVTYPE'] == 'CPX', 'sv_type_detail'] = df.pop('CPX_TYPE')
        invalid_details = df['sv_type_detail'].dropna()[
            ~df['sv_type_detail'].dropna().isin(SV_TYPE_DETAILS)
        ]
        if not invalid_details.empty:
            msg = f'Unexpected enum value: {invalid_details.iloc[0]}'
            raise ValueError(msg)

        if 'CPX_INTERVALS' in df.columns:
            df['CPX_INTERVALS'] = (
                df['CPX_INTERVALS']
                .str.split(',')
                .map(
                    lambda intervals: [
                        self._parse_cpx_interval(interval) for interval in intervals
                    ],
                    na_action='ignore',
                )
            )
        else:
            df['CPX_INTERVALS'] = None

        gencode_df = self._read_parquet(self.input()[1])
        consequences_by_variant = annotate_gene_consequences(df, gencode_df)
        df['sortedGeneConsequences'] = [
            consequences_by_variant.get(variant, []) for variant in df.index
        ]

        # Add gnomad frequency
        gnomad_df = self._read_parquet(self.input()[2])
        gnomad_lookup = match_gnomad_af(df, gnomad_df)
        df['populations'] = df['ID'].map(
            lambda vid: {'gnomad_svs': gnomad_lookup.get(vid)},
        )

        # Add StrVCTVRE
        with self._open_parquet(self.input()[3]) as f:
            strvctvre = run_strvctvre(df, f)
        df['predictions'] = df.index.map(lambda vid: {'strvctvre': strvctvre.get(vid)})

        df['svDetail'] = df.pop('CPX_INTERVALS').map(
            lambda v: {'cpxIntervals': v} if isinstance(v, list) and v else {},
        )
        df['svDetail'] = df['svDetail'].combine(
            df.pop('sv_type_detail'),
            lambda d, v: d | {'typeDetail': v} if pd.notna(v) else d,
        )
        if 'CHR2' in df:
            has_source = (
                (df['SVTYPE'] == 'INS')
                & df['CHR2'].notna()
                & (df['CHR2'] != df['#CHROM'])
            )
            df.loc[has_source, 'svDetail'] = df.loc[has_source, 'svDetail'].combine(
                df.loc[has_source, 'CHR2'],
                lambda d, chrom: d | {'sourceChrom': chrom.removeprefix('chr')},
            )
        df['svDetail'] = df['svDetail'].map(json.dumps)

        # Add serial integer index
        max_key_line = self.find_vcf_header_line(self.input()[0][0], '##maxKey')
        curr_max_key = int(max_key_line.removeprefix('##maxKey=').strip())
        df['key'] = range(curr_max_key + 1, curr_max_key + 1 + len(df))

        added_columns = df.columns.difference(original_columns)
        id_cols = ['key', 'ID']
        rename_cols = {'ID': 'variantId', 'SVTYPE': 'svType'}
        cols = sorted({*added_columns, *rename_cols} - set(id_cols))
        return df[[*id_cols, *cols]].rename(columns=rename_cols)

    @staticmethod
    def _open_parquet(input_target: luigi.Target):
        input_target.format = luigi.format.Nop
        return input_target.open()

    @classmethod
    def _read_parquet(cls, input_target: luigi.Target, **kwargs) -> pd.DataFrame:
        with cls._open_parquet(input_target) as f:
            return pd.read_parquet(f, **kwargs)

    @staticmethod
    def _parse_cpx_interval(interval):
        # an example format of CPX_INTERVALS is "DUP_chr1:1499897-1499974"
        sv_type, loc = interval.split('_chr')
        if sv_type not in SV_TYPES:
            msg = f'Unexpected enum value: {sv_type}'
            raise ValueError(msg)
        contig, pos = loc.split(':')
        start, end = pos.split('-')
        return {
            'chrom': contig,
            'start': int(start),
            'end': int(end),
            'type': sv_type,
        }
