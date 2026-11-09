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

CPX_INTERVALS = 'CPX_INTERVALS'
CPX_TYPE = 'CPX_TYPE'
CHR2 = 'CHR2'
END2 = 'END2'
SVLEN = 'SVLEN'

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

SV_TYPES = ['DEL', 'DUP', 'INS', 'INV', 'CPX', 'BND', 'CTX', 'CNV']

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

SEGMENT_COLUMNS = ['variant', 'segment_type', 'contig', 'start', 'end']


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
            gene_id=lambda df: df['attributes'].str.extract(
                r'gene_id "([^"]*)"',
                expand=False,
            ),
            tss=lambda df: np.where(df['strand'] == '-', df['end'], df['start']),
        )[['contig', 'start', 'end', 'strand', 'gene_id', 'tss', 'transcript_id']]
        .reset_index(drop=True)
    )
    features = gtf[~is_transcript][['transcript_id', 'feature_type', 'start', 'end']]

    negative_strand = transcripts['strand'] == '-'
    promoters = (
        pd.DataFrame(
            {
                'contig': transcripts['contig'],
                'start': np.where(
                    negative_strand,
                    transcripts['tss'] + 1,
                    np.maximum(transcripts['tss'] - PROMOTER_WINDOW, 1),
                ),
                'end': np.where(
                    negative_strand,
                    transcripts['tss'] + PROMOTER_WINDOW,
                    transcripts['tss'] - 1,
                ),
                'gene_id': transcripts['gene_id'],
            },
        )
        .drop_duplicates(['contig', 'start', 'end'], keep='last')
        .reset_index(drop=True)
    )
    tss = (
        transcripts[['contig', 'tss', 'gene_id']]
        .drop_duplicates(['contig', 'tss'], keep='last')
        .sort_values('tss')
        .reset_index(drop=True)
    )
    return transcripts, features, promoters, tss


def _variants(df):
    info = df.reindex(
        columns=['END', CHR2, END2, SVLEN, CPX_TYPE, CPX_INTERVALS],
    ).astype(object)
    alt = df['ALT']
    multiallelic = alt.str.contains(',')
    if multiallelic.any():
        msg = f'Expected single ALT allele, found multiple: {alt[multiallelic].iloc[0]}'
        raise ValueError(msg)

    is_breakend = alt.str.contains(r'[\[\]]')
    sv_type = alt.str.extract(r'^<([^:>]+)[^>]*>$', expand=False).where(
        ~is_breakend,
        np.where(info[CPX_INTERVALS].notna(), 'CPX', 'BND'),
    )
    unexpected = ~sv_type.isin(SV_TYPES)
    if unexpected.any():
        msg = (
            f'Unexpected ALT allele: {alt[unexpected].iloc[0]}. Expected breakpoint or '
            'symbolic ALT allele representing a structural variant record.'
        )
        raise ValueError(msg)

    pos = df['POS'].astype(int)
    variants = pd.DataFrame(
        {
            'chrom': df['#CHROM'],
            'pos': pos,
            'end': pd.to_numeric(info['END'])
            .fillna(pos + df['REF'].str.len() - 1)
            .astype(int),
            'sv_type': sv_type,
            'complex_type': info[CPX_TYPE],
            'chr2': info[CHR2],
            'end2': pd.to_numeric(info[END2]).fillna(pos).astype(int),
            'sv_len': pd.to_numeric(info[SVLEN]).fillna(0).astype(int),
            'cpx_intervals': info[CPX_INTERVALS],
        },
    ).reset_index(drop=True)
    variants['includes_dispersed_dup'] = variants['complex_type'].isin(
        COMPLEX_SUBTYPES_WITH_DISPERSED_DUP,
    )

    is_complex = variants['sv_type'] == 'CPX'
    if (is_complex & variants['cpx_intervals'].isna()).any():
        msg = 'Complex (CPX) variant must contain CPX_INTERVALS INFO field'
        raise ValueError(msg)
    if (is_complex & variants['complex_type'].isna()).any():
        msg = 'Complex (CPX) variant must contain CPX_TYPE INFO field'
        raise ValueError(msg)
    if ((variants['sv_type'] == 'CTX') & variants['chr2'].isna()).any():
        msg = (
            'Translocation (CTX) variant represented as a single record must '
            'contain CHR2 INFO field'
        )
        raise ValueError(msg)
    return variants


def _segment_frame(variants, segment_type, contig, start, end):
    return pd.DataFrame(
        {
            'variant': variants.index,
            'segment_type': segment_type,
            'contig': contig,
            'start': start,
            'end': end,
        },
    )


def _subtract_dups_from_inversions(inversions, dups):
    inversions = inversions.drop_duplicates('variant', keep='last').set_index('variant')
    dups = dups.assign(dup_rank=dups.groupby('variant').cumcount())
    for _, rank_dups in dups.groupby('dup_rank'):
        rank_dups = rank_dups.set_index('variant')
        variants = inversions.index.intersection(rank_dups.index)
        inv = inversions.loc[variants]
        dup = rank_dups.loc[variants]
        invalid = (
            (inv['start'] > dup['end'])
            | (dup['start'] > inv['end'])
            | ((dup['start'] <= inv['start']) & (inv['end'] <= dup['end']))
        )
        if invalid.any():
            msg = f'Cannot subtract DUP from INV for variant {invalid.idxmax()}'
            raise ValueError(msg)
        keeps_left = inv['start'] < dup['start']
        inversions.loc[variants, 'start'] = inv['start'].where(keeps_left, dup['end'])
        inversions.loc[variants, 'end'] = dup['start'].where(keeps_left, inv['end'])
    return inversions.reset_index()


def _complex_segments(variants):
    intervals = variants['cpx_intervals'].str.split(',').explode()
    parsed = intervals.str.extract(r'^([^_]+)_(.+):(\d+)-(\d+)$')
    segments = pd.DataFrame(
        {
            'variant': intervals.index,
            'segment_type': parsed[0].to_numpy(),
            'contig': parsed[1].to_numpy(),
            'start': parsed[2].astype(int).to_numpy(),
            'end': parsed[3].astype(int).to_numpy(),
        },
    )
    segments = segments.assign(
        complex_type=variants.loc[segments['variant'], 'complex_type'].to_numpy(),
        type_rank=segments['segment_type'].map({t: i for i, t in enumerate(SV_TYPES)}),
    ).sort_values(['variant', 'contig', 'start', 'end', 'type_rank'])

    is_inversion = segments['segment_type'] == 'INV'
    dropped = (
        is_inversion
        & segments['complex_type'].isin(COMPLEX_SUBTYPES_WITHOUT_INVERSION)
    ) | ((segments['segment_type'] == 'INS') & (segments['complex_type'] == 'INS_iDEL'))
    adjusted = is_inversion & segments['complex_type'].isin(
        COMPLEX_SUBTYPES_WITH_DUP_ADJUSTED_INVERSION,
    )
    return pd.concat(
        [
            segments[~dropped & ~adjusted],
            _subtract_dups_from_inversions(
                segments[adjusted],
                segments[segments['segment_type'] == 'DUP'],
            ),
        ],
    )[SEGMENT_COLUMNS]


def _segments(variants):
    sv_type = variants['sv_type']
    simple = variants[~sv_type.isin(['CPX', 'CTX', 'BND', 'INS'])]
    insertions = variants[
        (sv_type == 'INS') | ((sv_type == 'CPX') & (variants['complex_type'] == 'dDUP'))
    ]
    translocations = variants[sv_type == 'CTX']
    complex_variants = variants[
        (sv_type == 'CPX')
        | (
            (sv_type == 'CTX')
            & (variants['complex_type'] == 'CTX_INV')
            & variants['cpx_intervals'].notna()
        )
    ]

    breakends = variants[sv_type == 'BND']
    breakend_type = np.where(
        breakends['complex_type'].isin(TRANSLOCATION_BREAKEND_SUBTYPES),
        'CTX',
        'BND',
    )
    same_chrom = breakends['chr2'] == breakends['chrom']
    second_breakend_conditions = [
        same_chrom & (breakends['sv_len'] > 0),
        same_chrom & (breakends['end2'] != breakends['pos']),
        ~same_chrom & breakends['chr2'].notna(),
    ]
    has_second_breakend = np.logical_or.reduce(second_breakend_conditions)
    second_breakend = np.select(
        second_breakend_conditions,
        [
            breakends['pos'] + breakends['sv_len'],
            breakends['end2'],
            breakends['end2'],
        ],
    )

    return pd.concat(
        [
            _segment_frame(
                simple,
                simple['sv_type'],
                simple['chrom'],
                simple['pos'],
                simple['end'],
            ),
            _segment_frame(
                insertions,
                'INS',
                insertions['chrom'],
                insertions['pos'],
                insertions['pos'] + 1,
            ),
            _segment_frame(
                breakends,
                breakend_type,
                breakends['chrom'],
                breakends['pos'],
                breakends['pos'],
            ),
            _segment_frame(
                breakends[has_second_breakend],
                breakend_type[has_second_breakend],
                breakends['chrom'].where(same_chrom, breakends['chr2'])[has_second_breakend],
                second_breakend[has_second_breakend],
                second_breakend[has_second_breakend],
            ),
            *(
                _segment_frame(translocations, 'CTX', contig, position, position)
                for contig, position in [
                    (translocations['chrom'], translocations['pos']),
                    (translocations['chrom'], translocations['end']),
                    (translocations['chr2'], translocations['end2']),
                    (translocations['chr2'], translocations['end2'] + 1),
                ]
            ),
            _complex_segments(complex_variants),
        ],
        ignore_index=True,
    )


def _overlapping_pairs(left, right):
    right_by_contig = dict(list(right.groupby('contig')))
    pairs = []
    for contig, left_group in left.groupby('contig'):
        if contig not in right_by_contig:
            continue
        right_group = right_by_contig[contig].sort_values('start')
        right_starts = right_group['start'].to_numpy()
        right_ends = right_group['end'].to_numpy()
        max_length = (right_ends - right_starts).max()
        first = np.searchsorted(
            right_starts,
            left_group['start'].to_numpy() - max_length,
            side='left',
        )
        last = np.searchsorted(right_starts, left_group['end'].to_numpy(), side='right')
        counts = last - first
        candidates = np.repeat(first, counts) + (
            np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
        )
        left_starts = np.repeat(left_group['start'].to_numpy(), counts)
        overlapping = right_ends[candidates] >= left_starts
        pairs.append(
            pd.DataFrame(
                {
                    'left': np.repeat(left_group.index.to_numpy(), counts)[overlapping],
                    'right': right_group.index.to_numpy()[candidates[overlapping]],
                },
            ),
        )
    if not pairs:
        return pd.DataFrame({'left': [], 'right': []}, dtype=int)
    return pd.concat(pairs, ignore_index=True)


def _feature_stats(pairs, features):
    feature_overlaps = (
        pairs[['start', 'end', 'transcript_id']]
        .reset_index(names='pair')
        .merge(
            features.rename(
                columns={'start': 'feature_start', 'end': 'feature_end'},
            ),
            on='transcript_id',
        )
    )
    feature_overlaps = feature_overlaps[
        (feature_overlaps['start'] <= feature_overlaps['feature_end'])
        & (feature_overlaps['end'] >= feature_overlaps['feature_start'])
    ]
    spanned = (feature_overlaps['start'] <= feature_overlaps['feature_start']) & (
        feature_overlaps['feature_end'] <= feature_overlaps['end']
    )
    contains_segment = (feature_overlaps['feature_start'] <= feature_overlaps['start']) & (
        feature_overlaps['end'] <= feature_overlaps['feature_end']
    )
    return (
        feature_overlaps.assign(
            spanned=spanned,
            breakends=np.where(spanned, 0, np.where(contains_segment, 2, 1)),
        )
        .groupby(['pair', 'feature_type'])
        .agg(
            overlapping=('spanned', 'size'),
            spanned=('spanned', 'sum'),
            breakends=('breakends', 'sum'),
        )
        .unstack(fill_value=0)
        .reindex(
            index=pairs.index,
            columns=pd.MultiIndex.from_product(
                [['overlapping', 'spanned', 'breakends'], ['CDS', 'UTR']],
            ),
            fill_value=0,
        )
    )


def _transcript_consequences(segments, variants, transcripts, features):
    overlaps = _overlapping_pairs(segments, transcripts)
    segment = segments.loc[overlaps['left']].reset_index(drop=True)
    transcript = transcripts.loc[overlaps['right']].reset_index(drop=True)
    pairs = pd.DataFrame(
        {
            'variant': segment['variant'],
            'segment_type': segment['segment_type'],
            'start': segment['start'],
            'end': segment['end'],
            'includes_dispersed_dup': variants.loc[
                segment['variant'],
                'includes_dispersed_dup',
            ].to_numpy(),
            'gene_id': transcript['gene_id'],
            'transcript_id': transcript['transcript_id'],
            'transcript_start': transcript['start'],
            'transcript_end': transcript['end'],
            'tss': transcript['tss'],
        },
    )
    stats = _feature_stats(pairs, features)

    spans_transcript = (pairs['start'] <= pairs['transcript_start']) & (
        pairs['transcript_end'] <= pairs['end']
    )
    within_transcript = (pairs['transcript_start'] <= pairs['start']) & (
        pairs['end'] <= pairs['transcript_end']
    )
    tss_in_segment = (pairs['start'] <= pairs['tss']) & (pairs['tss'] <= pairs['end'])
    cds_breakends = stats[('breakends', 'CDS')]
    utr_breakends = stats[('breakends', 'UTR')]

    simple = np.select(
        [stats[('overlapping', 'CDS')] > 0, stats[('overlapping', 'UTR')] > 0],
        [LOF, UTR],
        INTRONIC,
    )
    deletion = np.where(tss_in_segment, LOF, simple)
    exon_dup = np.select(
        [
            (cds_breakends == 2) | ((cds_breakends == 1) & (utr_breakends == 1)),
            cds_breakends == 1,
            stats[('spanned', 'CDS')] > 0,
            (utr_breakends > 0) | (stats[('spanned', 'UTR')] > 0),
        ],
        [LOF, PARTIAL_EXON_DUP, INT_EXON_DUP, UTR],
        INTRONIC,
    )
    duplication = np.select(
        [spans_transcript, tss_in_segment, ~within_transcript],
        [COPY_GAIN, TSS_DUP, DUP_PARTIAL],
        exon_dup,
    )
    segment_type = pairs['segment_type']
    consequence = np.select(
        [
            segment_type == 'DEL',
            segment_type == 'INS',
            (segment_type == 'DUP')
            & ~spans_transcript
            & pairs['includes_dispersed_dup'],
            segment_type == 'DUP',
            segment_type == 'CNV',
            segment_type == 'INV',
            segment_type == 'CTX',
            segment_type == 'BND',
        ],
        [
            deletion,
            simple,
            None,
            duplication,
            np.where(
                np.isin(duplication, list(MSV_EXON_OVERLAP_CLASSIFICATIONS)),
                MSV_EXON_OVERLAP,
                duplication,
            ),
            np.where(spans_transcript, INV_SPAN, deletion),
            LOF,
            np.where(simple == LOF, BREAKEND_EXON, simple),
        ],
        None,
    )
    return pairs.assign(consequence=consequence).dropna(subset=['consequence'])[
        ['variant', 'consequence', 'gene_id']
    ]


def _promoter_consequences(segments, promoters, transcript_consequences):
    overlaps = _overlapping_pairs(segments, promoters)
    promoter_genes = pd.DataFrame(
        {
            'variant': segments.loc[overlaps['left'], 'variant'].to_numpy(),
            'gene_id': promoters.loc[overlaps['right'], 'gene_id'].to_numpy(),
        },
    ).merge(
        transcript_consequences[['variant', 'gene_id']].drop_duplicates(),
        how='left',
        indicator=True,
    )
    return promoter_genes[promoter_genes['_merge'] == 'left_only'][
        ['variant', 'gene_id']
    ].assign(consequence=PROMOTER)


def _nearest_tss_segments(segments, variants):
    is_merged = variants.loc[segments['variant'], 'complex_type'].isin(
        COMPLEX_SUBTYPES_WITH_MERGED_NEAREST_TSS,
    ).to_numpy()
    merged = segments[is_merged].sort_values(['variant', 'start'])
    previous_end = (
        merged.groupby('variant')['end'].cummax().groupby(merged['variant']).shift()
    )
    if (merged['start'] > previous_end + 1).any():
        msg = 'Complex variant segments need to be contiguous to find the nearest TSS'
        raise ValueError(msg)
    return pd.concat(
        [
            segments[~is_merged],
            merged.groupby('variant', as_index=False).agg(
                contig=('contig', 'first'),
                start=('start', 'min'),
                end=('end', 'max'),
            ),
        ],
        ignore_index=True,
    )


def _nearest_tss_consequences(segments, tss):
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
                    'gene_id': tss_by_contig[contig]['gene_id'].to_numpy()[nearest],
                },
            ),
        )
    if not nearest_genes:
        return pd.DataFrame(columns=['variant', 'gene_id', 'consequence'])
    return pd.concat(nearest_genes, ignore_index=True).assign(consequence=NEAREST_TSS)


def annotate_df(df, gtf_path):
    transcripts, features, promoters, tss = _load_annotations(gtf_path)
    variants = _variants(df)
    segments = _segments(variants)

    transcript_consequences = _transcript_consequences(
        segments,
        variants,
        transcripts,
        features,
    )
    regulatory_segments = segments[
        ~(
            (segments['segment_type'] == 'DUP')
            & variants.loc[segments['variant'], 'includes_dispersed_dup'].to_numpy()
        )
    ]
    promoter_consequences = _promoter_consequences(
        regulatory_segments,
        promoters,
        transcript_consequences,
    )
    genic_variants = set(
        transcript_consequences.loc[
            transcript_consequences['consequence'].isin(PROTEIN_CODING_CONSEQUENCES),
            'variant',
        ],
    ) | set(promoter_consequences['variant'])
    nearest_tss_consequences = _nearest_tss_consequences(
        _nearest_tss_segments(
            regulatory_segments[~regulatory_segments['variant'].isin(genic_variants)],
            variants,
        ),
        tss,
    )

    consequences = (
        pd.concat(
            [transcript_consequences, promoter_consequences, nearest_tss_consequences],
        )
        .drop_duplicates()
        .sort_values(['variant', 'consequence', 'gene_id'])
    )
    consequences_by_variant = (
        consequences.assign(
            gene_consequence=[
                {'geneId': gene_id, 'majorConsequence': consequence}
                for gene_id, consequence in zip(
                    consequences['gene_id'],
                    consequences['consequence'],
                    strict=True,
                )
            ],
        )
        .groupby('variant')['gene_consequence']
        .agg(list)
    )
    df['sortedGeneConsequences'] = [
        consequences_by_variant.get(variant, []) for variant in variants.index
    ]
    return df
