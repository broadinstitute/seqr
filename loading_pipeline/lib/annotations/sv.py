# ruff: noqa: N806
from typing import Any

import hail as hl

from loading_pipeline.lib.annotations import liftover
from loading_pipeline.lib.annotations.enums import (
    SV_CONSEQUENCE_RANKS,
    SV_TYPE_DETAILS,
    SV_TYPES,
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


SV_TYPES_LOOKUP = hl.dict(hl.enumerate(SV_TYPES, index_first=False))
SV_TYPE_DETAILS_LOOKUP = hl.dict(hl.enumerate(SV_TYPE_DETAILS, index_first=False))
SV_CONSEQUENCE_RANKS_LOOKUP = hl.dict(
    hl.enumerate(SV_CONSEQUENCE_RANKS, index_first=False),
)


def _get_cpx_interval(
    x: hl.StringExpression,
    reference_genome: ReferenceGenome,
) -> hl.StructExpression:
    # an example format of CPX_INTERVALS is "DUP_chr1:1499897-1499974"
    type_contig = x.split('_')
    contig_pos = type_contig[1].split(':')
    pos = contig_pos[1].split('-')
    return hl.struct(
        type_id=SV_TYPES_LOOKUP[type_contig[0]],
        start=hl.locus(
            contig_pos[0],
            hl.int32(pos[0]),
            reference_genome.value,
        ),
        end=hl.locus(
            contig_pos[0],
            hl.int32(pos[1]),
            reference_genome.value,
        ),
    )


def _sv_types(ht: hl.Table) -> hl.ArrayExpression:
    return ht.alleles[1].replace('[<>]', '').split(':', 2)


def alleles(ht: hl.Table, **_: Any) -> hl.ArrayExpression:
    return hl.array(
        [
            'N',
            hl.if_else(
                (
                    hl.is_defined(ht.sv_type_detail_id)
                    & (hl.array(SV_TYPES)[ht.sv_type_id] != 'CPX')
                ),
                hl.format(
                    '<%s:%s>',
                    hl.array(SV_TYPES)[ht.sv_type_id],
                    hl.array(SV_TYPE_DETAILS)[ht.sv_type_detail_id],
                ),
                hl.format('<%s>', hl.array(SV_TYPES)[ht.sv_type_id]),
            ),
        ],
    )


def info(ht: hl.Table, **_: Any) -> hl.StructExpression:
    return hl.Struct(
        ALGORITHMS=ht.algorithms,
        END=ht.start_locus.position,
        CHR2=ht.end_locus.contig,
        END2=ht.end_locus.position,
        SVTYPE=hl.array(SV_TYPES)[ht.sv_type_id],
        SVLEN=ht.sv_len,
    )


def locus(ht: hl.Table, **_: Any) -> hl.LocusExpression:
    return ht.start_locus


def algorithms(ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.str(',').join(ht['info.ALGORITHMS'])


def bothsides_support(ht: hl.Table, **_: Any) -> hl.Expression:
    return ht['info.BOTHSIDES_SUPPORT']


def CN(mt: hl.MatrixTable, **_: Any) -> hl.Expression:  # noqa: N802
    return mt.RD_CN


def concordance(mt: hl.MatrixTable, **_: Any) -> hl.Expression:
    is_called = hl.is_defined(mt.GT)
    was_previously_called = hl.is_defined(mt.CONC_ST) & ~mt.CONC_ST.contains(
        'EMPTY',
    )
    num_alt = hl.if_else(is_called, mt.GT.n_alt_alleles(), -1)
    prev_num_alt = hl.if_else(
        was_previously_called,
        PREVIOUS_GENOTYPE_N_ALT_ALLELES[hl.set(mt.CONC_ST)],
        -1,
    )
    concordant_genotype = num_alt == prev_num_alt
    discordant_genotype = (num_alt != prev_num_alt) & (prev_num_alt > 0)
    novel_genotype = (num_alt != prev_num_alt) & (prev_num_alt == 0)
    return hl.struct(
        prev_num_alt=hl.or_missing(discordant_genotype, prev_num_alt),
        prev_call=hl.or_missing(is_called, was_previously_called & concordant_genotype),
        new_call=hl.or_missing(is_called, ~was_previously_called | novel_genotype),
    )


def cpx_intervals(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
    **_: Any,
) -> hl.Expression:
    return hl.or_missing(
        hl.is_defined(ht['info.CPX_INTERVALS']),
        ht['info.CPX_INTERVALS'].map(lambda x: _get_cpx_interval(x, reference_genome)),
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


def gnomad_svs(
    ht: hl.Table,
    gnomad_svs_ht: hl.Table,
    **_: Any,
) -> hl.Expression:
    gnomad_svs_ht = gnomad_svs_ht.drop('locus', 'alleles')
    return gnomad_svs_ht.annotate(
        ID=gnomad_svs_ht.KEY,
    )[ht['info.GNOMAD_V4.1_TRUTH_VID']]


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
                gene_id=gencode_gene_symbol_to_gene_id_mapping.get(gene),
                major_consequence_id=SV_CONSEQUENCE_RANKS_LOOKUP[
                    gene_col.replace(CONSEQ_PREDICTED_PREFIX, '', 1)  # noqa: B023
                ],
            ),
        )
        for gene_col in CONSEQ_PREDICTED_GENE_COLS
    ]
    return hl.filter(hl.is_defined, mapped_genes).flatmap(lambda x: x)


def strvctvre(ht: hl.Table, **_: Any) -> hl.Expression:
    return hl.struct(score=hl.parse_float32(ht['info.StrVCTVRE']))


def sv_len(ht: hl.Table, **_: Any) -> hl.Expression:
    return ht['info.SVLEN']


def sv_type_id(ht: hl.Table, **_: Any) -> hl.Expression:
    return SV_TYPES_LOOKUP[_sv_types(ht)[0]]


def sv_type_detail_id(ht: hl.Table, **_: Any) -> hl.Expression:
    sv_types = _sv_types(ht)
    return hl.if_else(
        sv_types[0] == 'CPX',
        SV_TYPE_DETAILS_LOOKUP[ht['info.CPX_TYPE']],
        hl.or_missing(
            (sv_types[0] == 'INS') & (hl.len(sv_types) > 1),
            SV_TYPE_DETAILS_LOOKUP[sv_types[1]],
        ),
    )
