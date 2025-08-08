import hail as hl
import os

VLM_DATA_DIR = os.environ.get('VLM_DATA_DIR')


def get_hail_variant_counts(locus: hl.LocusExpression, ref: str, alt: str, genome_build: str) -> hl.Struct:
    interval = hl.eval(hl.interval(locus, locus, includes_start=True, includes_end=True))
    ht = hl.read_table(
        f'{VLM_DATA_DIR}/{genome_build}/SNV_INDEL/annotations.ht', _intervals=[interval], _filter_intervals=True,
    )
    ht = ht.filter(ht.alleles == hl.array([ref, alt]))

    counts = ht.aggregate(hl.agg.take(ht.gt_stats, 1))
    return (counts[0].AC, counts[0].hom) if counts else (0, 0)
