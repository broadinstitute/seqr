import subprocess  # nosec B404

import pandas as pd

from loading_pipeline.lib.annotations.enums import (
    COMPLEX_SUBTYPES_WITH_DUP_ADJUSTED_INVERSION,
    COMPLEX_SUBTYPES_WITH_OTHER_INVERSION,
    COMPLEX_SUBTYPES_WITH_DUP,
    COMPLEX_SUBTYPES_WITH_INSERTION,
)

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

MSV_EXON_OVERLAP_CLASSIFICATIONS = {
    LOF,
    INT_EXON_DUP,
    DUP_PARTIAL,
    PARTIAL_EXON_DUP,
    COPY_GAIN,
    TSS_DUP,
}
COMPLEX_SUBTYPES_WITH_DISPERSED_DUP = {
    *COMPLEX_SUBTYPES_WITH_DUP_ADJUSTED_INVERSION,
    *COMPLEX_SUBTYPES_WITH_DUP,
}
COMPLEX_SUBTYPES_WITH_MERGED_NEAREST_TSS = {
    *COMPLEX_SUBTYPES_WITH_INSERTION,
    *COMPLEX_SUBTYPES_WITH_OTHER_INVERSION,
    'dDUP_iDEL',
    'dupINVdel',
    'delINVdup',
}


def run_command(cmd: list[str]):
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603 # nosec B603
    except subprocess.CalledProcessError as e:
        e.add_note(e.stderr)
        raise


def annotate_gene_consequences(df: pd.DataFrame, gencode_df: pd.DataFrame) -> pd.DataFrame:
    # Implementation of gatk's SVAnnotate. Only change is to keep gene ID instead of gene symbol.
    # https://github.com/broadinstitute/gatk/blob/master/src/main/java/org/broadinstitute/hellbender/tools/walkers/sv/SVAnnotate.java

    transcripts, features = _load_annotations(gencode_df)
    segments = _segments(df)
    transcript_consequences = _transcript_consequences(segments, transcripts, features)

    regulatory_segments = segments[
        ~(
            (segments['segment_type'] == 'DUP')
            & segments['complex_type'].isin(COMPLEX_SUBTYPES_WITH_DISPERSED_DUP)
        )
    ]
    promoter_genes = _promoter_overlaps(regulatory_segments, transcripts).set_index(
        ['variant', 'geneId'],
    )
    transcript_genes = transcript_consequences.set_index(['variant', 'geneId']).index
    promoter_consequences = (
        promoter_genes[~promoter_genes.index.isin(transcript_genes)]
        .index.to_frame(index=False)
        .drop_duplicates()
        .assign(majorConsequence=PROMOTER)
    )

    annotated_variants = pd.concat(
        [transcript_consequences['variant'], promoter_consequences['variant']],
    )
    nearest_tss_consequences = _nearest_tss_consequences(
        regulatory_segments[~regulatory_segments['variant'].isin(annotated_variants)],
        transcripts,
    )

    consequences = pd.concat(
        [transcript_consequences, promoter_consequences, nearest_tss_consequences],
    )
    return (
        consequences.assign(
            gene_consequence=consequences[['geneId', 'majorConsequence']].to_dict('records'),
        )
        .groupby('variant')['gene_consequence']
        .agg(list)
    )

def _load_annotations(gencode_df):
    is_transcript = gencode_df['feature_type'] == 'transcript'
    transcripts = (
        gencode_df[is_transcript]
        .drop_duplicates(['contig', 'start', 'end'], keep='last')
        .rename(columns={'gene_id': 'geneId'})
        .assign(
            tss=lambda df: df['start'].mask(df['strand'] == '-', df['end']),
        )[['contig', 'start', 'end', 'strand', 'geneId', 'tss', 'transcriptId']]
    )
    features = gencode_df[~is_transcript][['transcriptId', 'feature_type', 'start', 'end']]

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
            & segments['complex_type'].isin({
                *COMPLEX_SUBTYPES_WITH_DUP,
                *COMPLEX_SUBTYPES_WITH_INSERTION,
        })
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
    segment_type = sv_type.mask(df['CPX_TYPE'] == 'dDUP', 'INS')
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

    complex_segments = _complex_segments(df[sv_type == 'CPX'])

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
        transcript_overlaps[['start', 'end', 'transcriptId']]
        .reset_index(names='transcript_overlap')
        .merge(features, on='transcriptId', suffixes=('', '_feature'))
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


def _promoter_overlaps(segments, transcripts):
    negative_strand = transcripts['strand'] == '-'
    promoters = transcripts.assign(
        start=(transcripts['tss'] - PROMOTER_WINDOW)
        .clip(lower=1)
        .mask(negative_strand, transcripts['tss'] + 1),
        end=(transcripts['tss'] - 1).mask(
            negative_strand,
            transcripts['tss'] + PROMOTER_WINDOW,
        ),
    ).drop_duplicates(['contig', 'start', 'end'], keep='last')
    promoter_overlaps = segments.merge(
        promoters,
        on='contig',
        suffixes=('', '_promoter'),
    )
    return promoter_overlaps[
        (promoter_overlaps['start'] <= promoter_overlaps['end_promoter'])
        & (promoter_overlaps['end'] >= promoter_overlaps['start_promoter'])
    ]


def _nearest_tss_consequences(segments, transcripts):
    is_merged = segments['complex_type'].isin(COMPLEX_SUBTYPES_WITH_MERGED_NEAREST_TSS)
    merged_segments = segments[is_merged].groupby('variant')
    segments = segments.assign(
        contig=segments['contig'].mask(
            is_merged,
            merged_segments['contig'].transform('first'),
        ),
        start=segments['start'].mask(
            is_merged,
            merged_segments['start'].transform('min'),
        ),
        end=segments['end'].mask(is_merged, merged_segments['end'].transform('max')),
    )

    tss = transcripts[['contig', 'tss', 'geneId']].drop_duplicates(
        ['contig', 'tss'],
        keep='last',
    )
    candidates = segments.reset_index(names='segment').merge(tss, on='contig')
    candidates['is_after'] = (candidates['tss'] > candidates['start']) | (
        (candidates['tss'] == candidates['start'])
        & (candidates['start'] == candidates['end'])
    )
    candidates['distance'] = candidates['start'] - candidates['tss'] - 1
    candidates.loc[candidates['is_after'], 'distance'] = (
        candidates['tss'] - candidates['end'] - 1
    )
    nearest_tss = candidates.sort_values(
        ['distance', 'is_after'],
        ascending=[True, False],
    ).drop_duplicates('segment')
    return (
        nearest_tss[['variant', 'geneId']]
        .drop_duplicates()
        .assign(majorConsequence=NEAREST_TSS)
    )
