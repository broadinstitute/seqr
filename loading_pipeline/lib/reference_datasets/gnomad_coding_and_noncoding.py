import hail as hl

from loading_pipeline.lib.annotations.enums import (
    TRANSCRIPT_CONSEQUENCE_TERMS,
)
from loading_pipeline.lib.annotations.expression_helpers import (
    get_expr_for_vep_sorted_transcript_consequences_array,
    get_expr_for_worst_transcript_consequence_annotations_struct,
)
from loading_pipeline.lib.core import ReferenceGenome

GNOMAD_CODING_NONCODING_HIGH_AF_THRESHOLD = 0.90
TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP = hl.dict(
    hl.enumerate(TRANSCRIPT_CONSEQUENCE_TERMS, index_first=False),
)


def get_ht(
    path: str,
    reference_genome: ReferenceGenome,
) -> hl.Table:
    ht = hl.read_table(path)
    filtered_contig = 'chr1' if reference_genome == ReferenceGenome.GRCh38 else '1'
    ht = hl.filter_intervals(
        ht,
        [
            hl.parse_locus_interval(
                filtered_contig,
                reference_genome=reference_genome.value,
            ),
        ],
    )
    ht = ht.filter(ht.freq[0].AF > GNOMAD_CODING_NONCODING_HIGH_AF_THRESHOLD)
    ht = ht.annotate(
        sorted_transaction_consequences=(
            get_expr_for_vep_sorted_transcript_consequences_array(
                ht.vep,
                omit_consequences=[],
            )
        ),
    )
    ht = ht.annotate(
        main_transcript=(
            get_expr_for_worst_transcript_consequence_annotations_struct(
                ht.sorted_transaction_consequences,
            )
        ),
    )
    ht = ht.select(
        coding=(
            ht.main_transcript.major_consequence_rank
            <= TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP['synonymous_variant']
        ),
        noncoding=(
            ht.main_transcript.major_consequence_rank
            >= TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP['downstream_gene_variant']
        ),
    )
    return ht.filter(ht.coding | ht.noncoding)
