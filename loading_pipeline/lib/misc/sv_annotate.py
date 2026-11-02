from collections import defaultdict

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


def _closed_interval(start, end):
    return pd.Interval(start, end, closed='both')


def _closed_intervals(starts, ends):
    return pd.arrays.IntervalArray.from_arrays(starts, ends, closed='both')


def _contains(outer, inner):
    return outer.left <= inner.left and inner.right <= outer.right


def _overlapping(df, interval):
    return df[df['interval'].array.overlaps(interval)]


def _subtract(a, b):
    if not a.overlaps(b) or _contains(b, a):
        raise ValueError(f'Cannot subtract {b} from {a}')
    if a.left < b.left:
        return _closed_interval(a.left, b.left)
    return _closed_interval(b.right, a.right)


def _merge_with_contiguous(a, b):
    if not (a.left <= b.right + 1 and b.left <= a.right + 1):
        raise ValueError(f'The two intervals need to be contiguous: {a} {b}')
    return _closed_interval(min(a.left, b.left), max(a.right, b.right))


def _count_breakends_inside_feature(variant, feature):
    if not feature.overlaps(variant) or _contains(variant, feature):
        return 0
    if _contains(feature, variant):
        return 2
    return 1


def _simple_consequence(variant, transcript):
    consequence = INTRONIC
    for feature_type, feature in transcript.features:
        if not variant.overlaps(feature):
            continue
        if feature_type == 'CDS':
            return LOF
        if feature_type == 'UTR':
            consequence = UTR
    return consequence


def _deletion_consequence(variant, transcript):
    if transcript.tss in variant:
        return LOF
    return _simple_consequence(variant, transcript)


def _duplication_consequence(variant, transcript, is_dispersed_duplication):
    if _contains(variant, transcript.interval):
        return COPY_GAIN
    if is_dispersed_duplication:
        return None
    if transcript.tss in variant:
        return TSS_DUP
    if not _contains(transcript.interval, variant):
        return DUP_PARTIAL
    breakpoints_in_cds = 0
    breakpoints_in_utr = 0
    cds_spanned = 0
    utr_spanned = 0
    for feature_type, feature in transcript.features:
        if not variant.overlaps(feature):
            continue
        spanned = _contains(variant, feature)
        if feature_type == 'CDS':
            if spanned:
                cds_spanned += 1
            else:
                breakpoints_in_cds += _count_breakends_inside_feature(variant, feature)
        elif feature_type == 'UTR':
            if spanned:
                utr_spanned += 1
            else:
                breakpoints_in_utr += _count_breakends_inside_feature(variant, feature)
    if breakpoints_in_cds == 2 or (breakpoints_in_cds == 1 and breakpoints_in_utr == 1):
        return LOF
    if breakpoints_in_cds == 1:
        return PARTIAL_EXON_DUP
    if cds_spanned > 0:
        return INT_EXON_DUP
    if breakpoints_in_utr > 0 or utr_spanned > 0:
        return UTR
    return INTRONIC


def _copy_number_variant_consequence(variant, transcript):
    consequence = _duplication_consequence(variant, transcript, False)
    if consequence in MSV_EXON_OVERLAP_CLASSIFICATIONS:
        return MSV_EXON_OVERLAP
    return consequence


def _inversion_consequence(variant, transcript):
    if _contains(variant, transcript.interval):
        return INV_SPAN
    return _deletion_consequence(variant, transcript)


def _breakend_consequence(variant, transcript):
    consequence = _simple_consequence(variant, transcript)
    return BREAKEND_EXON if consequence == LOF else consequence


def _transcript_consequence(variant, sv_type, includes_dispersed_dup, transcript):
    if sv_type == 'DEL':
        return _deletion_consequence(variant, transcript)
    if sv_type == 'INS':
        return _simple_consequence(variant, transcript)
    if sv_type == 'DUP':
        return _duplication_consequence(variant, transcript, includes_dispersed_dup)
    if sv_type == 'CNV':
        return _copy_number_variant_consequence(variant, transcript)
    if sv_type == 'INV':
        return _inversion_consequence(variant, transcript)
    if sv_type == 'CTX':
        return LOF
    if sv_type == 'BND':
        return _breakend_consequence(variant, transcript)
    return None


def _get_sv_type(alt, info):
    if ',' in alt:
        raise ValueError(f'Expected single ALT allele, found multiple: {alt}')
    if '[' in alt or ']' in alt:
        return 'CPX' if CPX_INTERVALS in info else 'BND'
    if alt.startswith('<') and alt.endswith('>'):
        sv_type = alt[1:-1].split(':')[0]
        if sv_type in SV_TYPES:
            return sv_type
    raise ValueError(
        f'Unexpected ALT allele: {alt}. Expected breakpoint or symbolic ALT allele representing a structural variant record.'
    )


def _parse_complex_intervals(cpx_intervals):
    segments = []
    for cpx_interval in cpx_intervals:
        sv_type, location = cpx_interval.split('_')[:2]
        contig, _, span = location.rpartition(':')
        start, end = span.split('-')
        segments.append((sv_type, contig, _closed_interval(int(start), int(end))))
    return sorted(
        segments,
        key=lambda segment: (
            segment[1],
            segment[2].left,
            segment[2].right,
            SV_TYPES.index(segment[0]),
        ),
    )


def _complex_annotation_segments(cpx_segments, complex_type):
    segments = []
    dup_intervals = []
    inversion_to_adjust = None
    for sv_type, contig, interval in cpx_segments:
        keep_segment = True
        if sv_type == 'INV':
            if complex_type in {'dDUP', 'dDUP_iDEL', 'INS_iDEL'}:
                keep_segment = False
            elif complex_type in {'dupINV', 'INVdup', 'dupINVdup', 'delINVdup', 'dupINVdel'}:
                inversion_to_adjust = (contig, interval)
                keep_segment = False
        elif sv_type == 'DUP':
            dup_intervals.append(interval)
        elif sv_type == 'INS' and complex_type == 'INS_iDEL':
            keep_segment = False
        if keep_segment:
            segments.append((sv_type, contig, interval))
    if inversion_to_adjust is not None:
        contig, interval = inversion_to_adjust
        for dup_interval in dup_intervals:
            interval = _subtract(interval, dup_interval)
        segments.append(('INV', contig, interval))
    return segments


def _get_sv_segments(chrom, pos, end, info, sv_type, complex_type):
    chr2 = info.get(CHR2)
    end2 = int(info[END2]) if END2 in info else pos
    cpx_intervals = info[CPX_INTERVALS].split(',') if CPX_INTERVALS in info else []
    if sv_type == 'CPX':
        if not cpx_intervals:
            raise ValueError('Complex (CPX) variant must contain CPX_INTERVALS INFO field')
        if complex_type is None:
            raise ValueError('Complex (CPX) variant must contain CPX_TYPE INFO field')
        segments = _complex_annotation_segments(
            _parse_complex_intervals(cpx_intervals), complex_type
        )
        if complex_type == 'dDUP':
            segments.append(('INS', chrom, _closed_interval(pos, pos + 1)))
        return segments
    if sv_type == 'CTX':
        if chr2 is None:
            raise ValueError(
                'Translocation (CTX) variant represented as a single record must contain CHR2 INFO field'
            )
        segments = []
        if complex_type == 'CTX_INV' and cpx_intervals:
            segments = _complex_annotation_segments(
                _parse_complex_intervals(cpx_intervals), complex_type
            )
        return [
            *segments,
            ('CTX', chrom, _closed_interval(pos, pos)),
            ('CTX', chrom, _closed_interval(end, end)),
            ('CTX', chr2, _closed_interval(end2, end2)),
            ('CTX', chr2, _closed_interval(end2 + 1, end2 + 1)),
        ]
    if sv_type == 'BND':
        sv_len = int(info.get(SVLEN, 0))
        segment_type = 'CTX' if complex_type in {'CTX_PP/QQ', 'CTX_PQ/QP'} else 'BND'
        segments = [(segment_type, chrom, _closed_interval(pos, pos))]
        if chr2 == chrom:
            if sv_len > 0:
                breakpoint = pos + sv_len
                segments.append((segment_type, chrom, _closed_interval(breakpoint, breakpoint)))
            elif end2 != pos:
                segments.append((segment_type, chrom, _closed_interval(end2, end2)))
        elif chr2 is not None:
            segments.append((segment_type, chr2, _closed_interval(end2, end2)))
        return segments
    if sv_type == 'INS':
        return [('INS', chrom, _closed_interval(pos, pos + 1))]
    return [(sv_type, chrom, _closed_interval(pos, end))]


def _segments_for_nearest_tss(segments, complex_type):
    if complex_type in {
        'INS_iDEL',
        'dDUP_iDEL',
        'delINV',
        'INVdel',
        'dupINVdel',
        'delINVdup',
        'delINVdel',
    }:
        _, contig, spanning = segments[0]
        for _, _, interval in segments[1:]:
            spanning = _merge_with_contiguous(spanning, interval)
        return [('DEL', contig, spanning)]
    return segments


def _load_transcripts(gtf_path):
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
            r'transcript_id "([^"]*)"', expand=False
        ),
    )
    is_transcript = gtf['feature_type'] == 'transcript'
    features = (
        gtf[~is_transcript]
        .assign(
            feature=lambda df: list(
                zip(df['feature_type'], _closed_intervals(df['start'], df['end']))
            )
        )
        .groupby('transcript_id')['feature']
        .agg(list)
    )
    return (
        gtf[is_transcript]
        .drop_duplicates(['contig', 'start', 'end'], keep='last')
        .assign(
            interval=lambda df: _closed_intervals(df['start'], df['end']),
            gene_id=lambda df: df['attributes'].str.extract(
                r'gene_id "([^"]*)"', expand=False
            ),
            tss=lambda df: np.where(df['strand'] == '-', df['end'], df['start']),
            features=lambda df: [features.get(t, []) for t in df['transcript_id']],
        )[['contig', 'interval', 'strand', 'gene_id', 'tss', 'features']]
    )


def _load_annotations_by_contig(gtf_path):
    transcripts = _load_transcripts(gtf_path)
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
            }
        )
        .drop_duplicates(['contig', 'start', 'end'], keep='last')
        .assign(interval=lambda df: _closed_intervals(df['start'], df['end']))
    )
    tss = (
        transcripts[['contig', 'tss', 'gene_id']]
        .drop_duplicates(['contig', 'tss'], keep='last')
        .sort_values('tss')
    )
    return (
        dict(list(transcripts.groupby('contig'))),
        dict(list(promoters.groupby('contig'))),
        {contig: df.reset_index(drop=True) for contig, df in tss.groupby('contig')},
    )


def _add_promoter_consequences(promoters, interval, consequences):
    coding_genes = set().union(*consequences.values())
    for gene in _overlapping(promoters, interval)['gene_id']:
        if gene not in coding_genes:
            consequences[PROMOTER].add(gene)


def _add_nearest_tss_consequence(tss, interval, consequences):
    positions = tss['tss']
    before_idx = positions.searchsorted(interval.left, side='right') - 1
    after_idx = positions.searchsorted(
        interval.left, side='left' if interval.left == interval.right else 'right'
    )
    distance_before = (
        interval.left - positions.iloc[before_idx] - 1 if before_idx >= 0 else np.inf
    )
    distance_after = (
        positions.iloc[after_idx] - interval.right - 1
        if after_idx < len(positions)
        else np.inf
    )
    nearest_idx = before_idx if distance_before < distance_after else after_idx
    consequences[NEAREST_TSS].add(tss['gene_id'].iloc[nearest_idx])


def _sorted_gene_consequences(
    record, transcripts_by_contig, promoters_by_contig, tss_by_contig
):
    info = {key: value for key, value in record.items() if pd.notna(value)}
    pos = int(record['POS'])
    end = int(info['END']) if 'END' in info else pos + len(record['REF']) - 1
    sv_type = _get_sv_type(record['ALT'], info)
    complex_type = info.get(CPX_TYPE)
    includes_dispersed_dup = complex_type in COMPLEX_SUBTYPES_WITH_DISPERSED_DUP
    segments = _get_sv_segments(record['#CHROM'], pos, end, info, sv_type, complex_type)

    consequences = defaultdict(set)
    for segment_type, contig, interval in segments:
        if contig not in transcripts_by_contig:
            continue
        for transcript in _overlapping(transcripts_by_contig[contig], interval).itertuples():
            consequence = _transcript_consequence(
                interval, segment_type, includes_dispersed_dup, transcript
            )
            if consequence is not None:
                consequences[consequence].add(transcript.gene_id)

    is_intergenic = not PROTEIN_CODING_CONSEQUENCES.intersection(consequences)

    if includes_dispersed_dup:
        segments = [segment for segment in segments if segment[0] != 'DUP']
    for _, contig, interval in segments:
        if contig not in promoters_by_contig:
            continue
        _add_promoter_consequences(promoters_by_contig[contig], interval, consequences)

    if is_intergenic and PROMOTER not in consequences:
        for _, contig, interval in _segments_for_nearest_tss(segments, complex_type):
            if contig not in tss_by_contig:
                continue
            _add_nearest_tss_consequence(tss_by_contig[contig], interval, consequences)

    return [
        {'geneId': gene_id, 'majorConsequence': consequence}
        for consequence in sorted(consequences)
        for gene_id in sorted(consequences[consequence])
    ]


def annotate_df(df, gtf_path):
    annotations_by_contig = _load_annotations_by_contig(gtf_path)
    df['sortedGeneConsequences'] = [
        _sorted_gene_consequences(record, *annotations_by_contig)
        for record in df.to_dict('records')
    ]
    return df
