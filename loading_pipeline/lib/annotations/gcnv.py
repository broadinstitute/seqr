from typing import Any

import hail as hl

from loading_pipeline.lib.annotations import expression_helpers, liftover
from loading_pipeline.lib.annotations.enums import SV_CONSEQUENCE_RANKS, SV_TYPES
from loading_pipeline.lib.core.definitions import ReferenceGenome
from loading_pipeline.lib.misc.gcnv import parse_gcnv_genes

SV_CONSEQUENCE_RANKS_LOOKUP = hl.dict(
    hl.enumerate(SV_CONSEQUENCE_RANKS, index_first=False),
)
SV_TYPES_LOOKUP = hl.dict(hl.enumerate(SV_TYPES, index_first=False))


def _start_and_end_equal(mt: hl.MatrixTable) -> hl.BooleanExpression:
    return (mt.sample_start == mt.start) & (mt.sample_end == mt.end)


def CN(mt: hl.MatrixTable, **_: Any) -> hl.Expression:  # noqa: N802
    return mt.CN


def concordance(
    mt: hl.MatrixTable,
    is_new_gcnv_joint_call: bool,
    **_: Any,
) -> hl.Expression:
    if is_new_gcnv_joint_call:
        return hl.or_missing(
            hl.is_defined(mt.GT),
            hl.struct(
                new_call=mt.no_ovl,
                prev_call=hl.len(mt.identical_ovl) > 0,
                prev_overlap=hl.len(mt.any_ovl) > 0,
            ),
        )
    return hl.or_missing(
        hl.is_defined(mt.GT),
        hl.struct(
            new_call=False,
            prev_call=~mt.is_latest,
            prev_overlap=False,
        ),
    )


def defragged(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    return mt.defragmented


def end_locus(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
    **_: Any,
) -> hl.LocusExpression:
    return hl.locus(ht.chr, ht.end, reference_genome.value)


def gt_stats(ht: hl.Table, callset_ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.struct(
        AF=hl.float32(callset_ht[ht.variant_id].sf),
        AC=callset_ht[ht.variant_id].sc,
        AN=hl.int32(callset_ht[ht.variant_id].sc / callset_ht[ht.variant_id].sf),
        Hom=hl.missing(hl.tint32),
        Het=hl.missing(hl.tint32),
    )


def GT(mt: hl.MatrixTable, **_: Any) -> hl.Expression:  # noqa: N802
    return hl.if_else(
        (mt.CN == 0) | (mt.CN > 3),  # noqa: PLR2004
        hl.Call([1, 1], phased=False),
        hl.Call([0, 1], phased=False),
    )


def num_exon(ht: hl.Table, **_: Any) -> hl.Expression:
    return ht.num_exon


def QS(mt: hl.MatrixTable, **_: Any) -> hl.Expression:  # noqa: N802
    return mt.QS


def rg37_locus(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression | None:
    liftover.add_rg38_liftover()
    return hl.liftover(
        start_locus(ht, ReferenceGenome.GRCh38),
        ReferenceGenome.GRCh37.value,
    )


def rg37_locus_end(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression | None:
    liftover.add_rg38_liftover()
    return hl.liftover(
        end_locus(ht, ReferenceGenome.GRCh38),
        ReferenceGenome.GRCh37.value,
    )


def sample_end(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    return hl.or_missing(
        ~_start_and_end_equal(mt),
        mt.sample_end,
    )


def sample_gene_ids(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    parsed_genes = parse_gcnv_genes(mt.genes_any_overlap_Ensemble_ID)
    return hl.or_missing(parsed_genes != mt.gene_ids, parsed_genes)


def sample_start(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    return hl.or_missing(
        ~_start_and_end_equal(mt),
        mt.sample_start,
    )


def sample_num_exon(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    return hl.or_missing(
        mt.genes_any_overlap_totalExons != mt.num_exon,
        mt.genes_any_overlap_totalExons,
    )


def sorted_gene_consequences(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression:
    return hl.array(
        ht.gene_ids.map(
            lambda gene: hl.Struct(
                gene_id=gene,
                major_consequence_id=hl.if_else(
                    ht.cg_genes.contains(gene),
                    SV_CONSEQUENCE_RANKS_LOOKUP['COPY_GAIN'],
                    hl.or_missing(
                        ht.lof_genes.contains(gene),
                        SV_CONSEQUENCE_RANKS_LOOKUP['LOF'],
                    ),
                ),
            ),
        ),
    )


def start_locus(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
    **_: Any,
) -> hl.LocusExpression:
    return hl.locus(ht.chr, ht.start, reference_genome.value)


def strvctvre(ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.struct(score=hl.parse_float32(ht.strvctvre_score))


def sv_type_id(ht: hl.Table, **_: Any) -> hl.Expression:
    return SV_TYPES_LOOKUP[ht.svtype]


def xpos(ht: hl.Table, reference_genome: ReferenceGenome, **_: Any) -> hl.Expression:
    return expression_helpers.get_expr_for_xpos(start_locus(ht, reference_genome))
