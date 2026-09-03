import hail as hl

from loading_pipeline.lib.core.definitions import ReferenceGenome
from loading_pipeline.lib.misc.io import split_multi_hts

BIALLELIC = 2


def compress_floats(ht: hl.Table):
    # Parse float64s into float32s to save space!
    return ht.select(
        **{
            k: hl.float32(v) if v.dtype == hl.tfloat64 else v
            for k, v in ht.row_value.items()
        },
    )


def filter_contigs(ht, reference_genome: ReferenceGenome):
    if hasattr(ht, 'interval'):
        return ht.filter(
            hl.set(reference_genome.standard_contigs).contains(
                ht.interval.start.contig,
            ),
        )
    # SV reference datasets are not keyed by locus.
    if hasattr(ht, 'locus'):
        return ht.filter(
            hl.set(reference_genome.standard_contigs).contains(ht.locus.contig),
        )
    return ht


def vcf_to_ht(
    file_name: str,
    reference_genome: ReferenceGenome,
    split_multi=False,
) -> hl.Table:
    mt = hl.import_vcf(
        file_name,
        reference_genome=reference_genome.value,
        drop_samples=True,
        skip_invalid_loci=True,
        contig_recoding=reference_genome.contig_recoding(include_mt=True),
        force_bgz=True,
        array_elements_required=False,
    )
    if split_multi:
        return split_multi_hts(mt, True).rows()

    # Validate that there exist no multialellic variants in the table.
    count_non_biallelic = mt.aggregate_rows(
        hl.agg.count_where(hl.len(mt.alleles) > BIALLELIC),
    )
    if count_non_biallelic:
        error = f'Encountered {count_non_biallelic} multiallelic variants'
        raise ValueError(error)
    return mt.rows()
