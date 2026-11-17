import os

import numpy as np
import pandas as pd
import pyBigWig
from joblib import load


def _features_overlap(df, features, window=0):
    overlap = df[['chrom', 'start', 'end', 'variant']].merge(features, left_on='chrom', right_on='feature_chrom')
    return overlap[
        (overlap['start'] - window < overlap['feature_end'])
        & (overlap['end'] + window > overlap['feature_start'])
    ]


def _bed_overlap(df, path, columns, window=0):
    features = pd.read_csv(path, sep='\t', names=['feature_chrom', 'feature_start', 'feature_end', *columns])
    return _features_overlap(df, features, window)


def _add_aggregates(df, overlap, **features):
    aggregated = overlap.groupby('variant').agg(
        **{name: (column, func) for name, (column, func, _) in features.items()},
    )
    fill_values = {name: default for name, (_, _, default) in features.items() if default is not None}
    return df.merge(aggregated, how='left', left_on='variant', right_index=True).fillna(fill_values)


TOP_N = 400


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


def _add_phylop_features(df, phylopPath):
    consBW = pyBigWig.open(phylopPath)
    x = []
    for chrom, start, end in zip(df['chrom'], df['start'], df['end']):
        if int(end) - int(start) > 1000000:
            x.append(np.array([15.0]))
        else:
            try:
                x.append(np.nan_to_num(np.array(consBW.values(chrom, int(start), int(end)))))
            except:
                x.append(np.array([0.5]))
    cons = [np.mean(y[np.argsort(y)[-TOP_N:]]) for y in x]
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
    group_columns = ['start', 'end', 'feature_start', 'feature_end', 'strand', 'cdsCount', 'size']
    variant_gene_groups = cds_overlap.groupby(['variant', 'gene'])[group_columns]
    first = variant_gene_groups.transform('first')
    last = variant_gene_groups.transform('last')
    overhang = (first['start'] - first['feature_start']).where(first['strand'] == 1, first['feature_end'] - first['end'])
    cds_overlap['early'] = first['cdsCount'] + overhang.clip(lower=0)

    plus_late = (last['end'] - last['feature_start']).where(last['end'] <= last['feature_end'], last['size'])
    minus_late = (last['feature_end'] - last['start']).where(last['start'] >= last['feature_start'], last['size'])
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


def annotate_strvctvre(svs, data_dir, phylopPath):
    # Implementation of StrVCTVRE: https://github.com/andrewSharo/StrVCTVRE/blob/master/StrVCTVRE.py

    df = svs[['chrom','start','end','svtype']]
    df['variant'] = df.index

    df['length'] = df['end'].astype(int) - df['start'].astype(int)
    df['DEL'] = df['svtype'] == 'DEL'
    df = df[df['length'] > 49]
    df = df[df['DEL'] | (df['svtype'] == 'DUP')]

    exon_overlap = _bed_overlap(
        df,
        'loading_pipeline/var/strvctre/exons_Appris_featurized_transcript_Chr1-Y_loeuf.sorted.bed',
        ['gene', 'exonRank', 'skippable', 'exonsInGene', 'const', 'pLI', 'loeuf'],
    )
    df = df[df['variant'].isin(exon_overlap['variant'])]

    scores = dict.fromkeys(df['variant'], 1.0)

    df = df[df['length'] < 3000000]
    if df.empty:
        svs['StrVCTVRE'] = svs.index.map(scores.get)
        return

    df = _add_exon_features(df, exon_overlap)
    df = _add_phylop_features(df, phylopPath)
    df = _add_tad_features(df)
    df = _add_cds_features(df)
    df = _add_usage_features(df)

    rf = load(os.path.join(data_dir, 'rfTrainedAllChromsPy3.joblib'))
    X = df[['DEL','numExonsFinal','phyloP', 'lowestExonRank', 'allSkippable','lowestExonsInGene', 'anyConstExon','pLIMax','loeufMin', 'cdsFracStartMin', 'cdsFracEndMax', 'cdsFracMax', 'pLI_max25_ID', 'loeuf_min25_ID','topExp','topUsage','maxStrength']]
    df['path'] = rf.predict_proba(X)[:,1]
    scores.update({variant: round(path, 3) for variant, path in zip(df['variant'], df['path'])})

    svs['StrVCTVRE'] = svs.index.map(scores.get)

