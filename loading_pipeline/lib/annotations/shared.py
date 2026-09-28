from typing import Any

import hail as hl

from loading_pipeline.lib.annotations import expression_helpers, liftover
from loading_pipeline.lib.annotations.vep import (
    transcript_consequences_sort,
    vep_85_transcript_consequences_select,
)
from loading_pipeline.lib.core.definitions import ReferenceGenome
from loading_pipeline.lib.tasks.exports.misc import sorted_hl_struct


def GT(mt: hl.MatrixTable, **_: Any) -> hl.Expression:  # noqa: N802
    return mt.GT


def GQ(mt: hl.MatrixTable, **_: Any) -> hl.Expression:  # noqa: N802
    is_called = hl.is_defined(mt.GT)
    return hl.if_else(is_called, mt.GQ, 0)


def rsid(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    return mt.rsid


def rg37_locus(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression | None:
    liftover.add_rg38_liftover()
    return hl.liftover(ht.locus, ReferenceGenome.GRCh37.value)


def xpos(ht: hl.Table, **_: Any) -> hl.Expression:
    return expression_helpers.get_expr_for_xpos(ht.locus)


def lifted_over_chrom(ht: hl.Table, **_: Any) -> hl.Expression:
    return expression_helpers.reference_independent_contig(
        ht.lifted_over_locus.contig,
    )


def lifted_over_pos(ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.or_missing(
        hl.is_defined(
            expression_helpers.reference_independent_contig(
                ht.lifted_over_locus.contig,
            ),
        ),
        ht.lifted_over_locus.position,
    )


def lifted_over_locus_end(ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.Struct(
        contig=expression_helpers.reference_independent_contig(
            ht.lifted_over_locus_end.contig,
        ),
        position=hl.or_missing(
            hl.is_defined(
                expression_helpers.reference_independent_contig(
                    ht.lifted_over_locus_end.contig,
                ),
            ),
            ht.lifted_over_locus_end.position,
        ),
    )


def variant_id(ht: hl.Table, **_: Any) -> hl.Expression:
    return expression_helpers.get_expr_for_variant_id(ht)


def sorted_transcript_consequences(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression:
    sorted_consequences = hl.sorted(
        ht.vep.transcript_consequences.map(
            vep_85_transcript_consequences_select,
        ).filter(lambda c: c.consequenceTerms.size() > 0),
        transcript_consequences_sort(ht),
    )
    return hl.enumerate(sorted_consequences).starmap(
        lambda i, s: sorted_hl_struct(
            s.annotate(
                majorConsequence=s.consequenceTerms.first(),
                transcriptRank=i,
            ),
        ),
    )
