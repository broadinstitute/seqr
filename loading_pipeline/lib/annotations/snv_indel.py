# ruff: noqa: N806
from typing import Any

import hail as hl

from loading_pipeline.lib.annotations import liftover
from loading_pipeline.lib.annotations.enums import (
    MOTIF_CONSEQUENCE_TERMS,
    REGULATORY_BIOTYPES,
    REGULATORY_CONSEQUENCE_TERMS,
)
from loading_pipeline.lib.annotations.vep import (
    transcript_consequences_sort,
    vep_110_transcript_consequences_select,
)
from loading_pipeline.lib.core.definitions import ReferenceGenome

MOTIF_CONSEQUENCE_TERMS_LOOKUP = hl.dict(
    hl.enumerate(MOTIF_CONSEQUENCE_TERMS, index_first=False),
)
REGULATORY_BIOTYPE_LOOKUP = hl.dict(
    hl.enumerate(REGULATORY_BIOTYPES, index_first=False),
)
REGULATORY_CONSEQUENCE_TERMS_LOOKUP = hl.dict(
    hl.enumerate(REGULATORY_CONSEQUENCE_TERMS, index_first=False),
)


def AB(mt: hl.MatrixTable, **_: Any) -> hl.Expression:  # noqa: N802
    is_called = hl.is_defined(mt.GT)
    return hl.bind(
        lambda total: hl.if_else(
            (is_called) & (total != 0) & (hl.len(mt.AD) > 1),
            hl.float32(mt.AD[1] / total),
            hl.missing(hl.tfloat32),
        ),
        hl.sum(mt.AD),
    )


def DP(mt: hl.MatrixTable, **_: Any) -> hl.Expression:  # noqa: N802
    is_called = hl.is_defined(mt.GT)
    return hl.if_else(
        is_called & hl.is_defined(mt.AD),
        hl.int32(hl.min(hl.sum(mt.AD), 32000)),
        hl.missing(hl.tint32),
    )


def rg38_locus(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression | None:
    liftover.add_rg37_liftover()
    return hl.liftover(ht.locus, ReferenceGenome.GRCh38.value)


def check_ref(ht: hl.Table, **_: Any) -> hl.BooleanExpression:
    return hl.is_defined(ht.vep.check_ref)


def sorted_motif_feature_consequences(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression:
    # NB: hl.min() doesn't work correctly in the "sorted" key expression, so we have an additional
    # is_defined check, even though the expression should work on missing on its own.
    # hail bug report incoming.
    return hl.or_missing(
        hl.is_defined(ht.vep.motif_feature_consequences),
        hl.sorted(
            ht.vep.motif_feature_consequences.map(
                lambda c: c.select(
                    consequence_term_ids=c.consequence_terms.map(
                        lambda t: MOTIF_CONSEQUENCE_TERMS_LOOKUP[t],
                    ),
                    motif_feature_id=c.motif_feature_id,
                ),
            ).filter(lambda c: c.consequence_term_ids.size() > 0),
            lambda c: hl.min(c.consequence_term_ids),
        ),
    )


def sorted_regulatory_feature_consequences(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression:
    return hl.or_missing(
        hl.is_defined(ht.vep.regulatory_feature_consequences),
        hl.sorted(
            ht.vep.regulatory_feature_consequences.map(
                lambda c: c.select(
                    biotype_id=REGULATORY_BIOTYPE_LOOKUP[c.biotype],
                    consequence_term_ids=c.consequence_terms.map(
                        lambda t: REGULATORY_CONSEQUENCE_TERMS_LOOKUP[t],
                    ),
                    regulatory_feature_id=c.regulatory_feature_id,
                ),
            ).filter(lambda c: c.consequence_term_ids.size() > 0),
            lambda c: hl.min(c.consequence_term_ids),
        ),
    )


def sorted_transcript_consequences(
    ht: hl.Table,
    gencode_ensembl_to_refseq_id_mapping: hl.tdict(hl.tstr, hl.tstr),
    **_: Any,
) -> hl.Expression:
    return hl.sorted(
        ht.vep.transcript_consequences.map(
            vep_110_transcript_consequences_select(
                gencode_ensembl_to_refseq_id_mapping,
            ),
        ).filter(lambda c: c.consequence_term_ids.size() > 0),
        transcript_consequences_sort(ht),
    )
