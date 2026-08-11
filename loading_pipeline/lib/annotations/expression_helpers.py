import hail as hl

from loading_pipeline.lib.annotations.enums import TRANSCRIPT_CONSEQUENCE_TERMS

TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP = hl.dict(
    hl.enumerate(TRANSCRIPT_CONSEQUENCE_TERMS, index_first=False),
)
HGVSC_CONSEQUENCES = hl.set(
    ['splice_donor_variant', 'splice_acceptor_variant', 'splice_region_variant'],
)
OMIT_TRANSCRIPT_CONSEQUENCE_TERMS = [
    'upstream_gene_variant',
    'downstream_gene_variant',
]
PROTEIN_LETTERS_1TO3 = hl.dict(
    {
        'A': 'Ala',
        'C': 'Cys',
        'D': 'Asp',
        'E': 'Glu',
        'F': 'Phe',
        'G': 'Gly',
        'H': 'His',
        'I': 'Ile',
        'K': 'Lys',
        'L': 'Leu',
        'M': 'Met',
        'N': 'Asn',
        'P': 'Pro',
        'Q': 'Gln',
        'R': 'Arg',
        'S': 'Ser',
        'T': 'Thr',
        'V': 'Val',
        'W': 'Trp',
        'Y': 'Tyr',
        'X': 'Ter',
        '*': 'Ter',
        'U': 'Sec',
    },
)


def _replace_chr_prefix(contig: str):
    return contig.replace('^chr', '')


def _get_expr_for_contig(locus: hl.expr.LocusExpression) -> hl.expr.StringExpression:
    """Normalized contig name"""
    return _replace_chr_prefix(locus.contig)


def _get_expr_for_contig_number(
    locus: hl.expr.LocusExpression,
) -> hl.expr.Int32Expression:
    """Convert contig name to contig number"""
    return hl.bind(
        lambda contig: (
            hl.case()
            .when(contig == 'X', 23)
            .when(contig == 'Y', 24)
            .when(contig[0] == 'M', 25)
            .default(hl.int(contig))
        ),
        _get_expr_for_contig(locus),
    )


def _get_expr_for_formatted_hgvs(csq):
    return hl.cond(
        hl.is_missing(csq.hgvsp) | HGVSC_CONSEQUENCES.contains(csq.major_consequence),
        csq.hgvsc.split(':')[-1],
        hl.cond(
            csq.hgvsp.contains('=') | csq.hgvsp.contains('%3D'),
            hl.bind(
                lambda protein_letters: 'p.'
                + protein_letters
                + hl.str(csq.protein_start)
                + protein_letters,
                hl.delimit(
                    csq.amino_acids.split('').map(
                        lambda pl: PROTEIN_LETTERS_1TO3.get(pl),
                    ),
                    '',
                ),
            ),
            csq.hgvsp.split(':')[-1],
        ),
    )


def get_expr_for_variant_id(table, max_length=None):
    """Expression for computing <chrom>-<pos>-<ref>-<alt>. Assumes alleles were split.

    Args:
        max_length: (optional) length at which to truncate the <chrom>-<pos>-<ref>-<alt> string

    Return:
        string: "<chrom>-<pos>-<ref>-<alt>"
    """
    contig = _get_expr_for_contig(table.locus)
    variant_id = (
        contig
        + '-'
        + hl.str(table.locus.position)
        + '-'
        + table.alleles[0]
        + '-'
        + table.alleles[1]
    )
    if max_length is not None:
        return variant_id[0:max_length]
    return variant_id


def get_expr_for_xpos(locus: hl.expr.LocusExpression) -> hl.expr.Int64Expression:
    """Genomic position represented as a single number = contig_number * 10**9 + position.
    This represents chrom:pos more compactly and allows for easier sorting.
    """
    contig_number = _get_expr_for_contig_number(locus)
    return hl.int64(contig_number) * 1_000_000_000 + locus.position


def get_expr_for_vep_sorted_transcript_consequences_array(
    vep_root,
    include_coding_annotations=True,
    omit_consequences=OMIT_TRANSCRIPT_CONSEQUENCE_TERMS,
):
    """Sort transcripts by 3 properties:

        1. coding > non-coding
        2. transcript consequence severity
        3. canonical > non-canonical

    so that the 1st array entry will be for the coding, most-severe, canonical transcript (assuming
    one exists).

    Also, for each transcript in the array, computes these additional fields:
        domains: converts Array[Struct] to string of comma-separated domain names
        hgvs: set to hgvsp is it exists, or else hgvsc. formats hgvsp for synonymous variants.
        major_consequence: set to most severe consequence for that transcript (
            VEP sometimes provides multiple consequences for a single transcript)
        major_consequence_rank: major_consequence rank based on VEP SO ontology (most severe = 1)
            (see http://www.ensembl.org/info/genome/variation/predicted_data.html)
        category: set to one of: "lof", "missense", "synonymous", "other" based on the value of major_consequence.

    Args:
        vep_root (StructExpression): root path of the VEP struct in the MT
        include_coding_annotations (bool): if True, fields relevant to protein-coding variants will be included
    """

    selected_annotations = [
        'biotype',
        'canonical',
        'cdna_start',
        'cdna_end',
        'codons',
        'exon',
        'gene_id',
        'gene_symbol',
        'hgvsc',
        'hgvsp',
        'intron',
        'transcript_id',
    ]

    if include_coding_annotations:
        selected_annotations.extend(
            [
                'amino_acids',
                'lof',
                'lof_filter',
                'lof_flags',
                'lof_info',
                'protein_id',
                'protein_start',
            ],
        )

    omit_consequence_terms = (
        hl.set(omit_consequences) if omit_consequences else hl.empty_set(hl.tstr)
    )

    result = hl.sorted(
        vep_root.transcript_consequences.map(
            lambda c: c.select(
                *selected_annotations,
                consequence_terms=c.consequence_terms.filter(
                    lambda t: ~omit_consequence_terms.contains(t),
                ),
                domains=c.domains.map(lambda domain: domain.db + ':' + domain.name),
                major_consequence=hl.cond(
                    c.consequence_terms.size() > 0,
                    hl.sorted(
                        c.consequence_terms,
                        key=lambda t: TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP.get(t),
                    )[0],
                    hl.null(hl.tstr),
                ),
            ),
        )
        .filter(lambda c: c.consequence_terms.size() > 0)
        .map(
            lambda c: c.annotate(
                category=(
                    hl.case()
                    .when(
                        TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP.get(c.major_consequence)
                        <= TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP.get(
                            'frameshift_variant',
                        ),
                        'lof',
                    )
                    .when(
                        TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP.get(c.major_consequence)
                        <= TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP.get(
                            'missense_variant',
                        ),
                        'missense',
                    )
                    .when(
                        TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP.get(c.major_consequence)
                        <= TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP.get(
                            'synonymous_variant',
                        ),
                        'synonymous',
                    )
                    .default('other')
                ),
                hgvs=_get_expr_for_formatted_hgvs(c),
                major_consequence_rank=TRANSCRIPT_CONSEQUENCE_TERM_RANK_LOOKUP.get(
                    c.major_consequence,
                ),
            ),
        ),
        lambda c: (
            hl.bind(
                lambda is_coding, is_most_severe, is_canonical: (
                    hl.cond(
                        is_coding,
                        hl.cond(
                            is_most_severe,
                            hl.cond(is_canonical, 1, 2),
                            hl.cond(is_canonical, 3, 4),
                        ),
                        hl.cond(
                            is_most_severe,
                            hl.cond(is_canonical, 5, 6),
                            hl.cond(is_canonical, 7, 8),
                        ),
                    )
                ),
                hl.or_else(c.biotype, '') == 'protein_coding',
                hl.set(c.consequence_terms).contains(vep_root.most_severe_consequence),
                hl.or_else(c.canonical, 0) == 1,
            )
        ),
    )

    if not include_coding_annotations:
        # for non-coding variants, drop fields here that are hard to exclude in the above code
        result = result.map(lambda c: c.drop('domains', 'hgvsp'))

    return hl.zip_with_index(result).map(
        lambda csq_with_index: csq_with_index[1].annotate(
            transcript_rank=csq_with_index[0],
        ),
    )


def get_expr_for_worst_transcript_consequence_annotations_struct(
    vep_sorted_transcript_consequences_root,
    include_coding_annotations=True,
):
    """Retrieves the top-ranked transcript annotation based on the ranking computed by
    get_expr_for_vep_sorted_transcript_consequences_array(..)

    Args:
        vep_sorted_transcript_consequences_root (ArrayExpression):
        include_coding_annotations (bool):
    """

    transcript_consequences = {
        'biotype': hl.tstr,
        'canonical': hl.tint,
        'category': hl.tstr,
        'cdna_start': hl.tint,
        'cdna_end': hl.tint,
        'codons': hl.tstr,
        'gene_id': hl.tstr,
        'gene_symbol': hl.tstr,
        'hgvs': hl.tstr,
        'hgvsc': hl.tstr,
        'major_consequence': hl.tstr,
        'major_consequence_rank': hl.tint,
        'transcript_id': hl.tstr,
    }

    if include_coding_annotations:
        transcript_consequences.update(
            {
                'amino_acids': hl.tstr,
                'domains': hl.tstr,
                'hgvsp': hl.tstr,
                'lof': hl.tstr,
                'lof_flags': hl.tstr,
                'lof_filter': hl.tstr,
                'lof_info': hl.tstr,
                'protein_id': hl.tstr,
            },
        )

    return hl.cond(
        vep_sorted_transcript_consequences_root.size() == 0,
        hl.struct(
            **{
                field: hl.null(field_type)
                for field, field_type in transcript_consequences.items()
            },
        ),
        hl.bind(
            lambda worst_transcript_consequence: (
                worst_transcript_consequence.annotate(
                    domains=hl.delimit(hl.set(worst_transcript_consequence.domains)),
                ).select(*transcript_consequences.keys())
            ),
            vep_sorted_transcript_consequences_root[0],
        ),
    )
