from typing import Any

import hail as hl

from loading_pipeline.lib.annotations import expression_helpers, liftover
from loading_pipeline.lib.annotations.vep import (
    transcript_consequences_sort,
    vep_85_transcript_consequences_select,
)
from loading_pipeline.lib.core.definitions import ReferenceGenome


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


def variant_id(ht: hl.Table, **_: Any) -> hl.Expression:
    return expression_helpers.get_expr_for_variant_id(ht)


def sorted_transcript_consequences(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression:
    return hl.sorted(
        ht.vep.transcript_consequences.map(
            vep_85_transcript_consequences_select,
        ).filter(lambda c: c.consequence_term_ids.size() > 0),
        transcript_consequences_sort(ht),
    )
