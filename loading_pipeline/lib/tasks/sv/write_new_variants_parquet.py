import luigi
import luigi.util
import pandas as pd
from pyliftover import LiftOver

from loading_pipeline.lib.paths import (
    new_variants_parquet_path,
    valid_reference_dataset_path,
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
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.sv.write_deduplicated_vcf import (
    WriteDeduplicatedSvVcfTask,
)

GENCODE_RELEASE = 42


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewSvVariantsParquetTask(BaseWriteParquetFromVcfTask):
    @property
    def annotation_dependencies(self) -> dict[str, hl.Table]:
        deps = {
            'gencode_gene_symbol_to_gene_id_mapping': hl.literal(
                load_gencode_gene_symbol_to_gene_id(GENCODE_RELEASE),
            ),
        }
        for reference_dataset in ReferenceDataset:
            if (
                reference_dataset.formatting_annotation
                and self.dataset_type
                in reference_dataset.dataset_types(self.reference_genome)
            ):
                deps[f'{reference_dataset.value}_ht'] = hl.read_table(
                    valid_reference_dataset_path(
                        self.reference_genome,
                        reference_dataset,
                    ),
                )
        return deps

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            new_variants_parquet_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteDeduplicatedSvVcfTask),
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
        df[['liftedOverChrom', 'liftedOverPos']] = [self._liftover(lo, c, p) for c, p in zip(df['CHROM'], df['POS'])]
        end_chrom = df['CHR2'].where(df['END2'].notna()).fillna(df['CHROM'])
        end_pos = df['END2'].fillna(df['END']).astype(int)
        df['rg37LocusEnd'] = [
            {'contig': chrom, 'position': pos} if chrom else None
            for chrom, pos in (self._liftover(lo, c, p) for c, p in zip(end_chrom, end_pos))
        ]

        # Select down to the formatting annotations fields and
        # any reference dataset collection annotations.
        new_variants_ht = new_variants_ht.select(
            **{
                name: fn(
                    new_variants_ht,
                    **self.annotation_dependencies,
                    **self.param_kwargs,
                )
                for name, fn in self.dataset_type.formatting_annotation_fns(
                    self.reference_genome,
                ).items()
            },
        )

        # Add serial integer index
        max_key_line = self.find_vcf_header_line(self.input()[0][0], '##maxKey')
        curr_max_key = int(max_key_line.removeprefix('##maxKey=').strip())
        df['key'] = range(curr_max_key + 1, curr_max_key + 1 + len(df))

        return df

    @staticmethod
    def _liftover(lo, chrom, pos):
        result = lo.convert_coordinate(chrom, pos)
        return (result[0][0], result[0][1] + 1) if result else (None, None)
