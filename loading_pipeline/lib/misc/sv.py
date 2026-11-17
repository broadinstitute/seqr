import subprocess  # nosec B404

import numpy as np
import pandas as pd

from loading_pipeline.lib.annotations.enums import (
    COMPLEX_SUBTYPES_WITH_DUP,
    COMPLEX_SUBTYPES_WITH_DUP_ADJUSTED_INVERSION,
    COMPLEX_SUBTYPES_WITH_INSERTION,
    COMPLEX_SUBTYPES_WITH_OTHER_INVERSION,
    SV_CONSEQUENCE_RANKS,
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


def annotate_gene_consequences(
    df: pd.DataFrame,
    gencode_df: pd.DataFrame,
) -> pd.DataFrame:
    # Implementation of gatk's SVAnnotate: https://github.com/broadinstitute/gatk/blob/master/src/main/java/org/broadinstitute/hellbender/tools/walkers/sv/SVAnnotate.java
    # Changes from base implementation:
    #     - Returns consequences on a per transcript basis instead of per gene
    #     - Returns gene ID instead of gene symbol
    #     - Does not annotate the consequences that are later dropped by seqr:
    #       PARTIAL_DISPERSED_DUP, NONCODING_SPAN, NONCODING_BREAKPOINT, and INTERGENIC
    #     - Does not handle cases for CPX_TYPE inputs that are not allowed through the input validation:
    #       CTX_PP/QQ, CTX_PQ_QP, and CTX_INV

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
        ['variant', 'geneId', 'transcriptId'],
    )
    transcript_genes = transcript_consequences.set_index(
        ['variant', 'geneId', 'transcriptId'],
    ).index
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
    ).sort_values(
        'majorConsequence',
        key=lambda c: c.map(SV_CONSEQUENCE_RANKS.index),
        kind='stable',
    )
    return (
        consequences.assign(
            gene_consequence=consequences[
                ['geneId', 'transcriptId', 'majorConsequence']
            ].to_dict('records'),
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
    features = gencode_df[~is_transcript][
        ['transcriptId', 'feature_type', 'start', 'end']
    ]

    return transcripts, features


def _complex_segments(df):
    segments = (
        df['CPX_INTERVALS']
        .explode()
        .rename_axis('variant')
        .reset_index(name='interval')
    )
    segments = segments.assign(
        segment_type=segments['interval'].str['type'],
        contig='chr' + segments['interval'].str['chrom'],
        start=segments['interval'].str['start'],
        end=segments['interval'].str['end'],
        complex_type=segments['variant'].map(df['sv_type_detail']),
    ).drop(columns='interval')

    segments = segments[
        ~(
            (segments['segment_type'] == 'INV')
            & segments['complex_type'].isin(
                {
                    *COMPLEX_SUBTYPES_WITH_DUP,
                    *COMPLEX_SUBTYPES_WITH_INSERTION,
                },
            )
        )
        & ~(
            (segments['segment_type'] == 'INS')
            & (segments['complex_type'] == 'INS_iDEL')
        )
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
    segment_type = sv_type.mask(df['sv_type_detail'] == 'dDUP', 'INS')
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
            'complex_type': df['sv_type_detail'],
        },
    )
    primary_segments = primary[primary['segment_type'] != 'CPX']

    breakends = df[sv_type == 'BND']
    same_chrom = breakends['end_chrom'] == breakends['#CHROM']
    sv_len = pd.to_numeric(breakends['SVLEN'])
    second_breakend = (
        breakends['END2']
        .fillna(df['POS'])
        .case_when(
            [
                (
                    same_chrom & (sv_len > 0),
                    breakends['POS'] + sv_len,
                ),
            ],
        )
    )
    second_breakend = second_breakend[
        ~(same_chrom & (second_breakend == breakends['POS']))
    ]
    second_breakend_segments = primary.loc[second_breakend.index].assign(
        contig=breakends['end_chrom'],
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
            (translocations['end_chrom'], translocations['END2'].fillna(df['POS'])),
            (translocations['end_chrom'], translocations['END2'].fillna(df['POS']) + 1),
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

    segment_type = transcript_overlaps['segment_type']
    transcript_overlaps = transcript_overlaps.assign(majorConsequence=INTRONIC)
    transcript_overlaps.loc[
        transcript_overlaps.index.isin(
            feature_overlaps.loc[
                feature_overlaps['feature_type'] == 'UTR',
                'transcript_overlap',
            ],
        ),
        'majorConsequence',
    ] = UTR
    transcript_overlaps.loc[
        transcript_overlaps.index.isin(
            feature_overlaps.loc[
                feature_overlaps['feature_type'] == 'CDS',
                'transcript_overlap',
            ],
        ),
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

    spanned = (feature_overlaps['start'] <= feature_overlaps['start_feature']) & (
        feature_overlaps['end_feature'] <= feature_overlaps['end']
    )
    spanned_features = feature_overlaps[spanned]
    partial_features = feature_overlaps[~spanned]
    start_breakpoints = partial_features[
        partial_features['start_feature'] <= partial_features['start']
    ]
    end_breakpoints = partial_features[
        partial_features['end'] <= partial_features['end_feature']
    ]
    cds_breakpoint = transcript_overlaps.index.isin(
        partial_features.loc[
            partial_features['feature_type'] == 'CDS',
            'transcript_overlap',
        ],
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
                transcript_overlaps.index.isin(start_breakpoints['transcript_overlap'])
                & transcript_overlaps.index.isin(end_breakpoints['transcript_overlap'])
                & cds_breakpoint,
                LOF,
            ),
            (cds_breakpoint, PARTIAL_EXON_DUP),
            (
                transcript_overlaps.index.isin(
                    spanned_features.loc[
                        spanned_features['feature_type'] == 'CDS',
                        'transcript_overlap',
                    ],
                ),
                INT_EXON_DUP,
            ),
            (
                transcript_overlaps.index.isin(
                    feature_overlaps.loc[
                        feature_overlaps['feature_type'] == 'UTR',
                        'transcript_overlap',
                    ],
                ),
                UTR,
            ),
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

    return transcript_overlaps.dropna(subset=['majorConsequence'])[
        ['variant', 'majorConsequence', 'geneId', 'transcriptId']
    ].drop_duplicates()


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

    tss = transcripts[['contig', 'tss', 'geneId', 'transcriptId']].drop_duplicates(
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
        nearest_tss[['variant', 'geneId', 'transcriptId']]
        .drop_duplicates()
        .assign(majorConsequence=NEAREST_TSS)
    )


MIN_STRVCTRE_LENGTH = 49
MAX_STRVCTRE_LENGTH = 3000000
TOP_N = 400


def run_strvctvre(df, phylop_file):
    # Implementation of StrVCTVRE: https://github.com/andrewSharo/StrVCTVRE/blob/master/StrVCTVRE.py

    df = df[['#CHROM', 'POS', 'END', 'SVTYPE']]
    df['DEL'] = df['SVTYPE'] == 'DEL'
    df = df[df['DEL'] | (df['SVTYPE'] == 'DUP')]
    df['length'] = df['END'] - df['POS']
    df = df[df['length'] > MIN_STRVCTRE_LENGTH]


    exon_overlap = _bed_overlap(
        df,
        'loading_pipeline/var/strvctre/exons_Appris_featurized_transcript_Chr1-Y_loeuf.sorted.bed',
        ['gene', 'exonRank', 'skippable', 'exonsInGene', 'const', 'pLI', 'loeuf'],
    )
    df = df[df.index.isin(exon_overlap.index)]

    scores = dict.fromkeys(df.index, 1.0)

    df = df[df['length'] < MAX_STRVCTRE_LENGTH]
    if df.empty:
        return scores

    df = _add_exon_features(df, exon_overlap)
    df = _add_phylop_features(df, phylop_file)
    df = _add_tad_features(df)
    df = _add_cds_features(df)
    df = _add_usage_features(df)

    df['path'] = _predict_pathogenicity(df)
    scores.update({variant: round(path, 3) for variant, path in zip(df.index, df['path'])})

    return scores


def _features_overlap(df, features, window=0):
    overlap = df[['#CHROM', 'POS', 'END']].join(features.set_index('feature_chrom'), on='#CHROM', how='inner')
    return overlap[
        (overlap['POS'] - window < overlap['feature_end'])
        & (overlap['END'] + window > overlap['feature_start'])
    ]


def _bed_overlap(df, path, columns, window=0):
    features = pd.read_csv(path, sep='\t', names=['feature_chrom', 'feature_start', 'feature_end', *columns])
    return _features_overlap(df, features, window)


def _add_aggregates(df, overlap, **features):
    aggregated = overlap.groupby(level=0).agg(
        **{name: (column, func) for name, (column, func, _) in features.items()},
    )
    fill_values = {name: default for name, (_, _, default) in features.items() if default is not None}
    return df.join(aggregated).fillna(fill_values)


def _predict_pathogenicity(df):
    model = np.load('loading_pipeline/var/strvctre/rfTrainedAllChromsPy3.npz')
    features = df[model['feature_names']].to_numpy(dtype=np.float32)
    nodes = np.tile(model['roots'], (len(features), 1))
    rows = np.arange(len(features))[:, None]
    for _ in range(int(model['max_depth'])):
        left = model['children_left'][nodes]
        go_left = features[rows, model['feature'][nodes]] <= model['threshold'][nodes]
        nodes = np.where(left == -1, nodes, np.where(go_left, left, model['children_right'][nodes]))
    leaf_proba = model['proba'][nodes]
    total = np.zeros(len(features))
    for tree in range(leaf_proba.shape[1]):
        total += leaf_proba[:, tree]
    return total / leaf_proba.shape[1]


def _add_exon_features(df, exon_overlap):
    return _add_aggregates(
        df,
        exon_overlap,
        numExonsFinal=('feature_start', 'size', None),
        allSkippable=('skippable', 'all', None),
        lowestExonRank=('exonRank', 'min', None),
        lowestExonsInGene=('exonsInGene', 'min', None),
        anyConstExon=('const', 'max', None),
        pLIMax=('pLI', 'max', None),
        loeufMin=('loeuf', 'min', None),
    )


def _add_phylop_features(df, phylop_file):
    starts = df['POS'].astype(int).to_numpy()
    ends = df['END'].astype(int).to_numpy()
    cons = np.empty(len(df))
    for chrom, positions in df.groupby('#CHROM').indices.items():
        phylop = pd.read_parquet(phylop_file, filters=[('chrom', '==', chrom)], columns=['phylop'])['phylop'].to_numpy()
        for i in positions:
            start, end = starts[i], ends[i]
            if end - start > 1000000:
                y = np.array([15.0])
            elif start >= end or end > len(phylop):
                y = np.array([0.5])
            else:
                y = np.nan_to_num(phylop[start:end].astype(np.float64))
            cons[i] = np.mean(y[np.argsort(y)[-TOP_N:]])
    df['phyloP'] = cons
    return df


def _add_tad_features(df):
    tad_overlap = _bed_overlap(df, 'loading_pipeline/var/strvctre/rep12tadsMergedhg38.bed', ['strength'])
    return _add_aggregates(df, tad_overlap, maxStrength=('strength', 'max', 0))


def _add_cds_features(df):
    cds_overlap = _bed_overlap(
        df,
        'loading_pipeline/var/strvctre/exons_CDS_Chr1-Y.sorted.bed',
        ['CDSLength', 'size', 'exonRank', 'strand', 'gene', 'cdsCount', 'pLI', 'loeuf'],
    )

    cds_overlap = cds_overlap.sort_values('exonRank')
    group_columns = ['POS', 'END', 'feature_start', 'feature_end', 'strand', 'cdsCount', 'size']
    variant_gene_groups = cds_overlap.groupby([cds_overlap.index, 'gene'])[group_columns]
    first = variant_gene_groups.transform('first')
    last = variant_gene_groups.transform('last')
    overhang = (first['POS'] - first['feature_start']).where(first['strand'] == 1, first['feature_end'] - first['END'])
    cds_overlap['early'] = first['cdsCount'] + overhang.clip(lower=0)

    plus_late = (last['END'] - last['feature_start']).where(last['END'] <= last['feature_end'], last['size'])
    minus_late = (last['feature_end'] - last['POS']).where(last['POS'] >= last['feature_start'], last['size'])
    cds_overlap['late'] = last['cdsCount'] + plus_late.where(last['strand'] == 1, minus_late)

    cds_overlap['cdsFracStart'] = cds_overlap['early']/cds_overlap['CDSLength']
    cds_overlap['cdsFracEnd'] = cds_overlap['late']/cds_overlap['CDSLength']
    cds_overlap['cdsFrac'] = (cds_overlap['late'] - cds_overlap['early'])/cds_overlap['CDSLength']

    covers_start_or_quarter = (cds_overlap['cdsFracStart'] == 0) | (cds_overlap['cdsFrac'] > 0.25)
    cds_overlap['pLI25'] = cds_overlap['pLI'].where(covers_start_or_quarter)
    cds_overlap['loeuf25'] = cds_overlap['loeuf'].where(covers_start_or_quarter)

    return _add_aggregates(
        df,
        cds_overlap,
        cdsFracStartMin=('cdsFracStart', 'min', 2),
        cdsFracEndMax=('cdsFracEnd', 'max', -1),
        cdsFracMax=('cdsFrac', 'max', -1),
        pLI_max25_ID=('pLI25', 'max', -1),
        loeuf_min25_ID=('loeuf25', 'min', 3),
    )


def _add_usage_features(df):
    usage = pd.read_csv(
        'loading_pipeline/var/strvctre/summary_exon_usage_hg38.sorted.bed',
        sep='\t',
        names=['feature_chrom', 'feature_start', 'feature_end', 'avgUsage', 'avgExp'],
    )
    usage_overlap = _features_overlap(df, usage)
    if usage_overlap.empty:
        usage_overlap = _features_overlap(df, usage, window=1000)
    if usage_overlap.empty:
        return df.assign(topUsage=usage.avgUsage.median(), topExp=usage.avgExp.median())

    df = _add_aggregates(
        df,
        usage_overlap,
        topUsage=('avgUsage', lambda x: x.nlargest(TOP_N).mean(), None),
        topExp=('avgExp', lambda x: x.nlargest(TOP_N).mean(), None),
    )
    return df.fillna({'topExp': df['topExp'].median(), 'topUsage': df['topUsage'].median()})
