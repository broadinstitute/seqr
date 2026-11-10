import numpy as np
import pandas as pd

LOF = 'LOF'
INT_EXON_DUP = 'INTRAGENIC_EXON_DUP'
COPY_GAIN = 'COPY_GAIN'
TSS_DUP = 'TSS_DUP'
DUP_PARTIAL = 'DUP_PARTIAL'
INTRONIC = 'INTRONIC'
PARTIAL_EXON_DUP = 'PARTIAL_EXON_DUP'
INV_SPAN = 'INV_SPAN'
UTR = 'UTR'
MSV_EXON_OVERLAP = 'MSV_EXON_OVERLAP'
PROMOTER = 'PROMOTER'
BREAKEND_EXON = 'BREAKEND_EXONIC'
NEAREST_TSS = 'NEAREST_TSS'

PROMOTER_WINDOW = 1000

GTF_COLUMNS = [
    'contig',
    'source',
    'feature_type',
    'start',
    'end',
    'score',
    'strand',
    'frame',
    'attributes',
]

MSV_EXON_OVERLAP_CLASSIFICATIONS = {
    LOF,
    INT_EXON_DUP,
    DUP_PARTIAL,
    PARTIAL_EXON_DUP,
    COPY_GAIN,
    TSS_DUP,
}
PROTEIN_CODING_CONSEQUENCES = {
    *MSV_EXON_OVERLAP_CLASSIFICATIONS,
    INV_SPAN,
    MSV_EXON_OVERLAP,
    UTR,
    INTRONIC,
    BREAKEND_EXON,
}
COMPLEX_SUBTYPES_WITH_DISPERSED_DUP = {
    'dDUP',
    'dupINV',
    'INVdup',
    'dupINVdup',
    'dupINVdel',
    'delINVdup',
    'dDUP_iDEL',
}
COMPLEX_SUBTYPES_WITHOUT_INVERSION = {'dDUP', 'dDUP_iDEL', 'INS_iDEL'}
COMPLEX_SUBTYPES_WITH_DUP_ADJUSTED_INVERSION = {
    'dupINV',
    'INVdup',
    'dupINVdup',
    'delINVdup',
    'dupINVdel',
}
COMPLEX_SUBTYPES_WITH_MERGED_NEAREST_TSS = {
    'INS_iDEL',
    'dDUP_iDEL',
    'delINV',
    'INVdel',
    'dupINVdel',
    'delINVdup',
    'delINVdel',
}
TRANSLOCATION_BREAKEND_SUBTYPES = {'CTX_PP/QQ', 'CTX_PQ/QP'}


def _load_annotations(gtf_path):
    gtf = pd.read_csv(
        gtf_path,
        sep='\t',
        comment='#',
        header=None,
        names=GTF_COLUMNS,
        usecols=['contig', 'feature_type', 'start', 'end', 'strand', 'attributes'],
    )
    gtf = gtf[gtf['feature_type'].isin(['transcript', 'CDS', 'UTR'])].assign(
        transcript_id=lambda df: df['attributes'].str.extract(
            r'transcript_id "([^"]*)"',
            expand=False,
        ),
    )
    is_transcript = gtf['feature_type'] == 'transcript'
    transcripts = (
        gtf[is_transcript]
        .drop_duplicates(['contig', 'start', 'end'], keep='last')
        .assign(
            geneId=lambda df: df['attributes'].str.extract(
                r'gene_id "([^"]*)"',
                expand=False,
            ),
            tss=lambda df: df['start'].mask(df['strand'] == '-', df['end']),
        )[['contig', 'start', 'end', 'strand', 'geneId', 'tss', 'transcript_id']]
    )
    features = gtf[~is_transcript][['transcript_id', 'feature_type', 'start', 'end']]

    return transcripts, features


def _complex_segments(df):
    segments = (
        df['CPX_INTERVALS']
        .str.split(',')
        .explode()
        .rename_axis('variant')
        .reset_index(name='interval')
    )
    parsed = segments['interval'].str.extract(
        r'^(?P<segment_type>[^_]+)_(?P<contig>.+):(?P<start>\d+)-(?P<end>\d+)$',
    )
    segments = segments.assign(
        segment_type=parsed['segment_type'],
        contig=parsed['contig'],
        start=parsed['start'].astype(int),
        end=parsed['end'].astype(int),
        complex_type=segments['variant'].map(df['CPX_TYPE']),
    ).drop(columns='interval')

    segments = segments[
        ~(
            (segments['segment_type'] == 'INV')
            & segments['complex_type'].isin(COMPLEX_SUBTYPES_WITHOUT_INVERSION)
        )
        & ~((segments['segment_type'] == 'INS') & (segments['complex_type'] == 'INS_iDEL'))
    ]

    is_dup_adjusted_inversion = (segments['segment_type'] == 'INV') & (
        segments['complex_type'].isin(COMPLEX_SUBTYPES_WITH_DUP_ADJUSTED_INVERSION)
    )
    dups = segments[segments['segment_type'] == 'DUP']
    inversion_start = dups['variant'].map(
        segments[is_dup_adjusted_inversion].set_index('variant')['start'],
    )
    trims_end = dups['start'] > inversion_start
    new_end = dups[trims_end].set_index('variant')['start']
    new_start = dups[inversion_start.notna() & ~trims_end].set_index('variant')['end']

    return segments.assign(
        start=segments['variant']
        .map(new_start)
        .where(is_dup_adjusted_inversion)
        .fillna(segments['start']),
        end=segments['variant']
        .map(new_end)
        .where(is_dup_adjusted_inversion)
        .fillna(segments['end']),
    )


def _segments(df):
    sv_type = df['SVTYPE']
    segment_type = sv_type.case_when(
        [
            (df['CPX_TYPE'] == 'dDUP', 'INS'),
            (df['CPX_TYPE'].isin(TRANSLOCATION_BREAKEND_SUBTYPES), 'CTX'),
        ],
    )
    primary = pd.DataFrame(
        {
            'variant': df.index,
            'segment_type': segment_type,
            'contig': df['#CHROM'],
            'start': df['POS'],
            'end': df['END'].case_when(
                [
                    (segment_type == 'INS', df['POS'] + 1),
                    (segment_type.isin(['BND', 'CTX']), df['POS']),
                ],
            ),
            'complex_type': df['CPX_TYPE'],
        },
    )
    primary_segments = primary[primary['segment_type'] != 'CPX']

    breakends = df[sv_type == 'BND']
    same_chrom = breakends['CHR2'] == breakends['#CHROM']
    second_breakend = breakends['END2'].case_when(
        [
            (
                same_chrom & (breakends['SVLEN'] > 0),
                breakends['POS'] + breakends['SVLEN'],
            ),
        ],
    )
    second_breakend = second_breakend[
        breakends['CHR2'].notna() & ~(same_chrom & (second_breakend == breakends['POS']))
    ]
    second_breakend_segments = primary.loc[second_breakend.index].assign(
        contig=breakends['CHR2'],
        start=second_breakend,
        end=second_breakend,
    )

    translocations = df[sv_type == 'CTX']
    translocation_segments = [
        primary.loc[translocations.index].assign(
            contig=contig,
            start=position,
            end=position,
        )
        for contig, position in [
            (translocations['#CHROM'], translocations['END']),
            (translocations['CHR2'], translocations['END2']),
            (translocations['CHR2'], translocations['END2'] + 1),
        ]
    ]

    complex_segments = _complex_segments(
        df[(sv_type == 'CPX') | ((df['CPX_TYPE'] == 'CTX_INV') & df['CPX_INTERVALS'].notna())],
    )

    return pd.concat(
        [
            primary_segments,
            second_breakend_segments,
            *translocation_segments,
            complex_segments,
        ],
        ignore_index=True,
    )


def _transcript_consequences(segments, transcripts, features):
    transcript_overlaps = segments.merge(
        transcripts,
        on='contig',
        suffixes=('', '_transcript'),
    )
    transcript_overlaps = transcript_overlaps[
        (transcript_overlaps['start'] <= transcript_overlaps['end_transcript'])
        & (transcript_overlaps['end'] >= transcript_overlaps['start_transcript'])
    ]

    feature_overlaps = (
        transcript_overlaps[['start', 'end', 'transcript_id']]
        .reset_index(names='transcript_overlap')
        .merge(features, on='transcript_id', suffixes=('', '_feature'))
    )
    feature_overlaps = feature_overlaps[
        (feature_overlaps['start'] <= feature_overlaps['end_feature'])
        & (feature_overlaps['end'] >= feature_overlaps['start_feature'])
    ]
    spanned = (feature_overlaps['start'] <= feature_overlaps['start_feature']) & (
        feature_overlaps['end_feature'] <= feature_overlaps['end']
    )
    contains_segment = (feature_overlaps['start_feature'] <= feature_overlaps['start']) & (
        feature_overlaps['end'] <= feature_overlaps['end_feature']
    )
    feature_overlaps = feature_overlaps.assign(
        spanned=spanned,
        breakends=(contains_segment + 1).mask(spanned, 0),
    )
    cds = feature_overlaps[feature_overlaps['feature_type'] == 'CDS']
    utr = feature_overlaps[feature_overlaps['feature_type'] == 'UTR']

    segment_type = transcript_overlaps['segment_type']
    transcript_overlaps = transcript_overlaps.assign(majorConsequence=INTRONIC)
    transcript_overlaps.loc[
        transcript_overlaps.index.isin(utr['transcript_overlap']),
        'majorConsequence',
    ] = UTR
    transcript_overlaps.loc[
        transcript_overlaps.index.isin(cds['transcript_overlap']),
        'majorConsequence',
    ] = LOF
    transcript_overlaps.loc[
        (segment_type == 'BND') & (transcript_overlaps['majorConsequence'] == LOF),
        'majorConsequence',
    ] = BREAKEND_EXON

    tss_in_segment = (transcript_overlaps['start'] <= transcript_overlaps['tss']) & (
        transcript_overlaps['tss'] <= transcript_overlaps['end']
    )
    transcript_overlaps.loc[
        segment_type.isin(['DEL', 'INV']) & tss_in_segment,
        'majorConsequence',
    ] = LOF

    spans_transcript = (
        transcript_overlaps['start'] <= transcript_overlaps['start_transcript']
    ) & (transcript_overlaps['end_transcript'] <= transcript_overlaps['end'])
    transcript_overlaps.loc[
        (segment_type == 'INV') & spans_transcript,
        'majorConsequence',
    ] = INV_SPAN

    transcript_overlaps.loc[segment_type == 'CTX', 'majorConsequence'] = LOF

    cds_breakends = (
        cds.groupby('transcript_overlap')['breakends']
        .sum()
        .reindex(transcript_overlaps.index, fill_value=0)
    )
    utr_breakends = (
        utr.groupby('transcript_overlap')['breakends']
        .sum()
        .reindex(transcript_overlaps.index, fill_value=0)
    )
    cds_spanned = transcript_overlaps.index.isin(
        cds.loc[cds['spanned'], 'transcript_overlap'],
    )
    utr_spanned = transcript_overlaps.index.isin(
        utr.loc[utr['spanned'], 'transcript_overlap'],
    )
    transcript_overlaps.loc[
        segment_type.isin(['DUP', 'CNV']),
        'majorConsequence',
    ] = transcript_overlaps['majorConsequence'].case_when(
        [
            (spans_transcript, COPY_GAIN),
            (tss_in_segment, TSS_DUP),
            (
                (transcript_overlaps['start'] < transcript_overlaps['start_transcript'])
                | (transcript_overlaps['end'] > transcript_overlaps['end_transcript']),
                DUP_PARTIAL,
            ),
            (
                (cds_breakends == 2) | ((cds_breakends == 1) & (utr_breakends == 1)),
                LOF,
            ),
            (cds_breakends == 1, PARTIAL_EXON_DUP),
            (cds_spanned, INT_EXON_DUP),
            ((utr_breakends > 0) | utr_spanned, UTR),
        ],
    )

    transcript_overlaps.loc[
        (segment_type == 'CNV')
        & transcript_overlaps['majorConsequence'].isin(
            MSV_EXON_OVERLAP_CLASSIFICATIONS,
        ),
        'majorConsequence',
    ] = MSV_EXON_OVERLAP

    transcript_overlaps.loc[
        (segment_type == 'DUP')
        & transcript_overlaps['complex_type'].isin(COMPLEX_SUBTYPES_WITH_DISPERSED_DUP)
        & ~spans_transcript,
        'majorConsequence',
    ] = None

    return (
        transcript_overlaps.dropna(subset=['majorConsequence'])[
            ['variant', 'majorConsequence', 'geneId']
        ]
        .drop_duplicates()
    )


def _promoter_consequences(segments, transcripts, transcript_consequences):
    negative_strand = transcripts['strand'] == '-'
    promoters = pd.DataFrame(
        {
            'contig': transcripts['contig'],
            'start': (transcripts['tss'] - PROMOTER_WINDOW)
            .clip(lower=1)
            .mask(negative_strand, transcripts['tss'] + 1),
            'end': (transcripts['tss'] - 1).mask(
                negative_strand,
                transcripts['tss'] + PROMOTER_WINDOW,
            ),
            'geneId': transcripts['geneId'],
        },
    ).drop_duplicates(['contig', 'start', 'end'], keep='last')
    promoter_genes = segments.merge(promoters, on='contig', suffixes=('', '_promoter'))
    promoter_genes = promoter_genes[
        (promoter_genes['start'] <= promoter_genes['end_promoter'])
        & (promoter_genes['end'] >= promoter_genes['start_promoter'])
    ][['variant', 'geneId']].merge(
        transcript_consequences[['variant', 'geneId']],
        how='left',
        indicator=True,
    )
    return (
        promoter_genes[promoter_genes['_merge'] == 'left_only'][['variant', 'geneId']]
        .drop_duplicates()
        .assign(majorConsequence=PROMOTER)
    )


def _nearest_tss_segments(segments):
    is_merged = segments['complex_type'].isin(COMPLEX_SUBTYPES_WITH_MERGED_NEAREST_TSS)
    return pd.concat(
        [
            segments[~is_merged],
            segments[is_merged].groupby('variant', as_index=False).agg(
                contig=('contig', 'first'),
                start=('start', 'min'),
                end=('end', 'max'),
            ),
        ],
        ignore_index=True,
    )


def _nearest_tss_consequences(segments, transcripts):
    tss = (
        transcripts[['contig', 'tss', 'geneId']]
        .drop_duplicates(['contig', 'tss'], keep='last')
        .sort_values('tss')
    )
    tss_by_contig = dict(list(tss.groupby('contig')))
    nearest_genes = []
    for contig, contig_segments in segments.groupby('contig'):
        if contig not in tss_by_contig:
            continue
        positions = tss_by_contig[contig]['tss'].to_numpy()
        starts = contig_segments['start'].to_numpy()
        ends = contig_segments['end'].to_numpy()
        before = np.searchsorted(positions, starts, side='right') - 1
        after = np.where(
            starts == ends,
            np.searchsorted(positions, starts, side='left'),
            before + 1,
        )
        distance_before = np.where(
            before >= 0,
            starts - positions[np.maximum(before, 0)] - 1,
            np.inf,
        )
        distance_after = np.where(
            after < len(positions),
            positions[np.minimum(after, len(positions) - 1)] - ends - 1,
            np.inf,
        )
        nearest = np.where(distance_before < distance_after, before, after)
        nearest_genes.append(
            pd.DataFrame(
                {
                    'variant': contig_segments['variant'].to_numpy(),
                    'geneId': tss_by_contig[contig]['geneId'].to_numpy()[nearest],
                },
            ),
        )
    if not nearest_genes:
        return pd.DataFrame(columns=['variant', 'geneId', 'majorConsequence'])
    return (
        pd.concat(nearest_genes, ignore_index=True)
        .drop_duplicates()
        .assign(majorConsequence=NEAREST_TSS)
    )


def annotate_df(df, gtf_path):
    transcripts, features = _load_annotations(gtf_path)
    segments = _segments(df)
    transcript_consequences = _transcript_consequences(segments, transcripts, features)
    regulatory_segments = segments[
        ~(
            (segments['segment_type'] == 'DUP')
            & segments['complex_type'].isin(COMPLEX_SUBTYPES_WITH_DISPERSED_DUP)
        )
    ]
    promoter_consequences = _promoter_consequences(
        regulatory_segments,
        transcripts,
        transcript_consequences,
    )
    genic_variants = set(
        transcript_consequences.loc[
            transcript_consequences['majorConsequence'].isin(PROTEIN_CODING_CONSEQUENCES),
            'variant',
        ],
    ) | set(promoter_consequences['variant'])
    nearest_tss_consequences = _nearest_tss_consequences(
        _nearest_tss_segments(
            regulatory_segments[~regulatory_segments['variant'].isin(genic_variants)],
        ),
        transcripts,
    )

    consequences = pd.concat(
        [transcript_consequences, promoter_consequences, nearest_tss_consequences],
    )
    consequences_by_variant = (
        consequences.assign(
            gene_consequence=consequences[['geneId', 'majorConsequence']].to_dict('records'),
        )
        .groupby('variant')['gene_consequence']
        .agg(list)
    )
    df['sortedGeneConsequences'] = [
        consequences_by_variant.get(variant, []) for variant in df.index
    ]
    return df
