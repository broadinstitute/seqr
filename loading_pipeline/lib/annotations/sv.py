# ruff: noqa: N806
from typing import Any

import hail as hl

from loading_pipeline.lib.annotations.enums import (
    SV_CONSEQUENCE_RANKS,
    validated_enum_member,
)

CONSEQ_PREDICTED_PREFIX = 'info.PREDICTED_'
CONSEQ_PREDICTED_GENE_COLS = {
    'info.PREDICTED_BREAKEND_EXONIC': hl.tarray(hl.tstr),
    'info.PREDICTED_COPY_GAIN': hl.tarray(hl.tstr),
    'info.PREDICTED_DUP_PARTIAL': hl.tarray(hl.tstr),
    'info.PREDICTED_INTRAGENIC_EXON_DUP': hl.tarray(hl.tstr),
    'info.PREDICTED_INTRONIC': hl.tarray(hl.tstr),
    'info.PREDICTED_INV_SPAN': hl.tarray(hl.tstr),
    'info.PREDICTED_LOF': hl.tarray(hl.tstr),
    'info.PREDICTED_MSV_EXON_OVERLAP': hl.tarray(hl.tstr),
    'info.PREDICTED_NEAREST_TSS': hl.tarray(hl.tstr),
    'info.PREDICTED_PARTIAL_EXON_DUP': hl.tarray(hl.tstr),
    'info.PREDICTED_PROMOTER': hl.tarray(hl.tstr),
    'info.PREDICTED_TSS_DUP': hl.tarray(hl.tstr),
    'info.PREDICTED_UTR': hl.tarray(hl.tstr),
}


def populations(
    ht: hl.Table,
    gnomad_svs_ht: hl.Table,
    **_: Any,
) -> hl.Expression:
    gnomad_sv_id = ht['info.GNOMAD_V4.1_TRUTH_VID']
    gnomad_sv = gnomad_svs_ht[gnomad_sv_id]
    return hl.struct(
        gnomad_svs=hl.or_missing(
            hl.is_defined(gnomad_sv),
            hl.struct(
                af=gnomad_sv.AF,
                het=gnomad_sv.N_HET,
                hom=gnomad_sv.N_HOM,
                id=gnomad_sv_id,
            ),
        ),
    )


def sorted_gene_consequences(
    ht: hl.Table,
    gencode_gene_symbol_to_gene_id_mapping: hl.tdict(hl.tstr, hl.tstr),
    **_: Any,
) -> hl.Expression:
    # In lieu of sorted_transcript_consequences seen on SNV/MITO.
    mapped_genes = [
        ht[gene_col].map(
            lambda gene: hl.struct(
                geneId=gencode_gene_symbol_to_gene_id_mapping.get(gene),
                majorConsequence=validated_enum_member(
                    gene_col.replace(CONSEQ_PREDICTED_PREFIX, '', 1),  # noqa: B023
                    SV_CONSEQUENCE_RANKS,
                ),
            ),
        )
        for gene_col in CONSEQ_PREDICTED_GENE_COLS
    ]
    return hl.filter(hl.is_defined, mapped_genes).flatmap(lambda x: x)
