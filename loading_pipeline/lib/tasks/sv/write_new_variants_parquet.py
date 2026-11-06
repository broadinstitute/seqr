import luigi
import luigi.util
import pandas as pd
from pyliftover import LiftOver

from loading_pipeline.lib.annotations.enums import (
    SV_TYPE_DETAILS,
    SV_TYPES,
)
from loading_pipeline.lib.paths import (
    new_variants_parquet_path,
)
from loading_pipeline.lib.reference_datasets.gencode.mapping_gene_ids import (
    load_gencode_gene_symbol_to_gene_id,
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

GENCODE_RELEASE = 42


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewSvVariantsParquetTask(BaseWriteParquetFromVcfTask):
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
                UpdatedReferenceDatasetParquetNoHailTask(reference_dataset=ReferenceDataset.gnomad_svs),
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

        # Run liftover
        lo = LiftOver('loading_pipeline/var/liftover/grch38_to_grch37.over.chain.gz')
        df[['liftedOverChrom', 'liftedOverPos']] = [self._liftover(lo, c, p) for c, p in zip(df['#CHROM'], df['POS'])]
        df['endChrom'] = df.pop('CHR2').where(df['END2'].notna())
        df['end'] = df.pop('END2').fillna(df.pop('END')).astype(int)
        df['rg37LocusEnd'] = [
            {'contig': chrom, 'position': pos} if chrom else None
            for chrom, pos in (
                self._liftover(lo, c, p)
                for c, p in zip(df['endChrom'].fillna(df['#CHROM']), df['end'])
            )
        ]

        # Annotate gene consequences
        gene_symbol_to_gene_id = load_gencode_gene_symbol_to_gene_id(GENCODE_RELEASE)
        predicted_csq_cols = [col for col in df.columns if col.startswith('PREDICTED_')]
        df['sortedGeneConsequences'] = df[predicted_csq_cols].apply(
            lambda row: [
                {
                    'geneId': gene_symbol_to_gene_id.get(gene),
                    'majorConsequence': col.removeprefix('PREDICTED_'),
                }
                for col, genes in row.dropna().items()
                for gene in genes.split(',')
            ],
            axis=1,
        )
        df = df.drop(columns=predicted_csq_cols)

        # Add gnomad frequency
        gnomad_input = self.input()[1]
        gnomad_input.format = luigi.format.Nop
        with gnomad_input.open() as f:
            gnomad_df = pd.read_parquet(f)
        gnomad_lookup = gnomad_df.set_index('id', drop=False).to_dict('index')
        df['populations'] = df.pop('GNOMAD_V4.1_TRUTH_VID').map(lambda vid: {'gnomad_svs': gnomad_lookup.get(vid)})

        # Select formatted annotations
        invalid_sv_types = df['SVTYPE'][~df['SVTYPE'].isin(SV_TYPES)]
        if not invalid_sv_types.empty:
            raise ValueError(f'Unexpected enum value: {invalid_sv_types.iloc[0]}')

        df.loc[df['SVTYPE'] == 'CPX', 'svTypeDetail'] = df.pop('CPX_TYPE')
        df.loc[df['SVTYPE'] == 'INS', 'svTypeDetail'] = df.pop('ALT').str.extract(r'^<[^:]+:(.+)>$')[0]
        invalid_details = df['svTypeDetail'].dropna()[~df['svTypeDetail'].dropna().isin(SV_TYPE_DETAILS)]
        if not invalid_details.empty:
            raise ValueError(f'Unexpected enum value: {invalid_details.iloc[0]}')

        df['cpxIntervals'] = df.pop('CPX_INTERVALS').str.split(',').map(
            lambda intervals: [self._parse_cpx_interval(interval) for interval in intervals],
            na_action='ignore',
        )

        df['chrom'] = df.pop('#CHROM').str.removeprefix('chr')
        df['endChrom'] = df['endChrom'].str.removeprefix('chr')
        df.loc[df['SVTYPE'] == 'INS', 'svSourceDetail'] = df['endChrom'].map(lambda chrom: {'chrom': chrom})
        df['endChrom'] = df['endChrom'].mask(df['SVTYPE'] == 'INS')
        df['xpos'] = df['chrom'].replace({'X': '23', 'Y': '24'}).astype(int) * 1_000_000_000 + df['POS']
        df['predictions'] = df.pop('StrVCTVRE').map(lambda score: {'strvctvre': score})

        df = df.rename(columns={
            'ALGORITHMS': 'algorithms',
            'BOTHSIDES_SUPPORT': 'bothsidesSupport',
            'POS': 'pos',
            'ID': 'variantId',
            'SVTYPE': 'svType',
        })

        # Add serial integer index
        max_key_line = self.find_vcf_header_line(self.input()[0][0], '##maxKey')
        curr_max_key = int(max_key_line.removeprefix('##maxKey=').strip())
        df['key'] = range(curr_max_key + 1, curr_max_key + 1 + len(df))

        return df

    @staticmethod
    def _liftover(lo, chrom, pos):
        result = lo.convert_coordinate(chrom, pos)
        return (result[0][0], result[0][1] + 1) if result else (None, None)

    @staticmethod
    def _parse_cpx_interval(interval):
        # an example format of CPX_INTERVALS is "DUP_chr1:1499897-1499974"
        type, loc = interval.split('_chr')
        if type not in SV_TYPES:
            raise ValueError(f'Unexpected enum value: {type}')
        contig, pos = loc.split(':')
        start, end = pos.split('-')
        return {
            'chrom': contig,
            'start': int(start),
            'end': int(end),
            'type': type,
        }
