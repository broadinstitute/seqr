# ruff: noqa: N806
from typing import Any

import hail as hl

from loading_pipeline.lib.annotations import liftover
from loading_pipeline.lib.annotations.enums import (
    SV_CONSEQUENCE_RANKS,
    SV_TYPE_DETAILS,
    SV_TYPES,
    validated_enum_member,
)
from loading_pipeline.lib.annotations.expression_helpers import (
    reference_independent_contig,
)
from loading_pipeline.lib.core.definitions import ReferenceGenome

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

PREVIOUS_GENOTYPE_N_ALT_ALLELES = hl.dict(
    {
        # Map of concordance string -> previous n_alt_alleles()
        # Concordant
        frozenset(['TN']): 0,  # 0/0 -> 0/0
        frozenset(['TP']): 2,  # 1/1 -> 1/1
        frozenset(['TN', 'TP']): 1,  # 0/1 -> 0/1
        # Novel
        frozenset(['FP']): 0,  # 0/0 -> 1/1
        frozenset(['TN', 'FP']): 0,  # 0/0 -> 0/1
        # Absent
        frozenset(['FN']): 2,  # 1/1 -> 0/0
        frozenset(['TN', 'FN']): 1,  # 0/1 -> 0/0
        # Discordant
        frozenset(['FP', 'TP']): 1,  # 0/1 -> 1/1
        frozenset(['FN', 'TP']): 2,  # 1/1 -> 0/1
    },
)


def _get_cpx_interval(
    x: hl.StringExpression,
) -> hl.StructExpression:
    # an example format of CPX_INTERVALS is "DUP_chr1:1499897-1499974"
    type_contig = x.split('_')
    contig_pos = type_contig[1].split(':')
    pos = contig_pos[1].split('-')
    return hl.struct(
        chrom=reference_independent_contig(contig_pos[0]),
        start=hl.int32(pos[0]),
        end=hl.int32(pos[1]),
        type=validated_enum_member(type_contig[0], SV_TYPES),
    )


def _sv_types(ht: hl.Table) -> hl.ArrayExpression:
    return ht.alleles[1].replace('[<>]', '').split(':', 2)


def algorithms(ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.str(',').join(ht['info.ALGORITHMS'])


def variant_id(ht: hl.Table, **_: Any) -> hl.Expression:
    return ht.variant_id


def bothsides_support(ht: hl.Table, **_: Any) -> hl.Expression:
    return ht['info.BOTHSIDES_SUPPORT']


def chrom(ht: hl.Table, **_: Any) -> hl.Expression:
    return reference_independent_contig(ht.locus.contig)


def end_chrom(ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.or_missing(
        ((sv_type(ht) != 'INS') & (ht.locus.contig != end_locus(ht).contig)),
        reference_independent_contig(end_locus(ht).contig),
    )


def sv_source_detail(ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.or_missing(
        ((sv_type(ht) == 'INS') & (ht.locus.contig != end_locus(ht).contig)),
        hl.Struct(chrom=reference_independent_contig(end_locus(ht).contig)),
    )


def CN(mt: hl.MatrixTable, **_: Any) -> hl.Expression:  # noqa: N802
    return mt.RD_CN


def _prev_num_alt(mt: hl.MatrixTable) -> hl.Expression:
    return hl.or_missing(
        hl.is_defined(mt.CONC_ST) & ~mt.CONC_ST.contains('EMPTY'),
        PREVIOUS_GENOTYPE_N_ALT_ALLELES[hl.set(mt.CONC_ST)],
    )


def new_call(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    prev_num_alt = _prev_num_alt(mt)
    novel_genotype = hl.if_else(
        hl.is_defined(prev_num_alt),
        (mt.GT.n_alt_alleles() != prev_num_alt) & (prev_num_alt == 0),
        True,
    )
    return hl.or_missing(hl.is_defined(mt.GT), novel_genotype)


def prev_call(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    prev_num_alt = _prev_num_alt(mt)
    concordant_genotype = hl.is_defined(prev_num_alt) & (
        mt.GT.n_alt_alleles() == prev_num_alt
    )
    return hl.or_missing(hl.is_defined(mt.GT), concordant_genotype)


def prev_num_alt(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    num_alt = hl.if_else(hl.is_defined(mt.GT), mt.GT.n_alt_alleles(), -1)
    prev_num_alt = _prev_num_alt(mt)
    discordant_genotype = (num_alt != prev_num_alt) & (prev_num_alt > 0)
    return hl.or_missing(discordant_genotype, prev_num_alt)


def cpx_intervals(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression:
    return hl.or_missing(
        hl.is_defined(ht['info.CPX_INTERVALS']),
        ht['info.CPX_INTERVALS'].map(_get_cpx_interval),
    )


def end_locus(ht: hl.Table, **_: Any) -> hl.StructExpression:
    rg38_lengths = hl.literal(hl.get_reference(ReferenceGenome.GRCh38.value).lengths)
    return hl.if_else(
        (
            hl.is_defined(ht['info.END2'])
            & (rg38_lengths[ht['info.CHR2']] >= ht['info.END2'])
        ),
        hl.locus(ht['info.CHR2'], ht['info.END2'], ReferenceGenome.GRCh38.value),
        hl.or_missing(
            (rg38_lengths[ht.locus.contig] >= ht['info.END']),
            hl.locus(ht.locus.contig, ht['info.END'], ReferenceGenome.GRCh38.value),
        ),
    )


def end(ht: hl.Table, **_: Any) -> hl.Expression:
    return end_locus(ht).position


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


def rg37_locus_end(
    ht: hl.Table,
    **_: Any,
) -> hl.Expression | None:
    liftover.add_rg38_liftover()
    end = end_locus(ht)
    return hl.or_missing(
        hl.is_defined(end),
        hl.liftover(
            hl.locus(
                end.contig,
                end.position,
                reference_genome=ReferenceGenome.GRCh38.value,
            ),
            ReferenceGenome.GRCh37.value,
        ),
    )


def pos(ht: hl.Table, **_: Any) -> hl.Expression:
    return ht.locus.position


def start_locus(ht: hl.Table, **_: Any):
    return ht.locus


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


def predictions(ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.struct(strvctvre=hl.parse_float32(ht['info.StrVCTVRE']))


def sv_type(ht: hl.Table, **_: Any) -> hl.Expression:
    return validated_enum_member(_sv_types(ht)[0], SV_TYPES)


def sv_type_detail(ht: hl.Table, **_: Any) -> hl.Expression:
    sv_types = _sv_types(ht)
    return hl.if_else(
        sv_types[0] == 'CPX',
        validated_enum_member(ht['info.CPX_TYPE'], SV_TYPE_DETAILS),
        hl.or_missing(
            (sv_types[0] == 'INS') & (hl.len(sv_types) > 1),
            validated_enum_member(sv_types[1], SV_TYPE_DETAILS),
        ),
    )
