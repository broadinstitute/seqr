import os

import numpy as np
import pandas as pd
import pyBigWig
from joblib import load


def read_bed(data_dir, file_name, names):
    return pd.read_csv(os.path.join(data_dir, file_name), sep='\t', names=names)


def _annotate_sv_features(df, exonOverlap, phylopPath, data_dir):
    exon_features = exonOverlap.groupby('variant').agg(
        numExonsFinal=('eStart', 'size'),
        allSkippable=('skippable', 'all'),
        lowestExonRank=('exonRank', 'min'),
        lowestExonsInGene=('exonsInGene', 'min'),
        anyConstExon=('const', 'max'),
        pLIMax=('pLI', 'max'),
        loeufMin=('loeuf', 'min'),
    )
    df = df.merge(exon_features, how='left', left_on='variant', right_index=True)

    size = 400

    consBW = pyBigWig.open(phylopPath)
    x = []
    for i in range(df.shape[0]):
        if int(df.loc[i,'end']) - int(df.loc[i,'start']) > 1000000:
            x.append(np.array([15.0]))
        else:
            try:
                x.append(np.nan_to_num(np.array(consBW.values(df.loc[i,'chrom'], int(df.loc[i,'start']), int(df.loc[i,'end'])))))
            except:
                x.append(np.array([0.5]))
    cons = [np.mean(y[np.argsort(y)[-size:]]) for y in x]
    df['phyloP'] = pd.Series(cons)

    tads = read_bed(data_dir, 'rep12tadsMergedhg38.bed', ['tChrom', 'tStart', 'tStop', 'strength'])
    tadOverlap = df[['chrom','start','end','variant']].merge(tads, left_on='chrom', right_on='tChrom')
    tadOverlap = tadOverlap[(tadOverlap['start'] < tadOverlap['tStop']) & (tadOverlap['end'] > tadOverlap['tStart'])]
    df = df.merge(
        tadOverlap.groupby('variant').agg(maxStrength=('strength', 'max')),
        how='left',
        left_on='variant',
        right_index=True,
    )
    df['maxStrength'].fillna(value=0, inplace=True)

    cds = read_bed(data_dir, 'exons_CDS_Chr1-Y.sorted.bed', ['cChrom', 'cStart', 'cStop', 'CDSLength', 'size', 'exonRank', 'strand','gene', 'cdsCount', 'pLI','loeuf'])
    cdsOverlap = df[['chrom','start','end','variant']].merge(cds, left_on='chrom', right_on='cChrom')
    cdsOverlap = cdsOverlap[(cdsOverlap['start'] < cdsOverlap['cStop']) & (cdsOverlap['end'] > cdsOverlap['cStart'])]
    exon_columns = ['start', 'end', 'cStart', 'cStop', 'strand', 'cdsCount', 'size']
    out = cdsOverlap.sort_values('exonRank')
    first = out.groupby(['variant', 'gene'])[exon_columns].transform('first')
    overhang = (first['start'] - first['cStart']).where(first['strand'] == 1, first['cStop'] - first['end'])
    out['early'] = first['cdsCount'] + overhang.clip(lower=0)

    out = out.sort_values('exonRank', ascending=False)
    last = out.groupby(['variant', 'gene'])[exon_columns].transform('first')
    plus_late = (last['end'] - last['cStart']).where(last['end'] <= last['cStop'], last['size'])
    minus_late = (last['cStop'] - last['start']).where(last['start'] >= last['cStart'], last['size'])
    out['late'] = last['cdsCount'] + plus_late.where(last['strand'] == 1, minus_late)

    out['cdsFracStart'] = out['early']/out['CDSLength']
    out['cdsFracEnd'] = out['late']/out['CDSLength']
    out['cdsFrac'] = (out['late'] - out['early'])/out['CDSLength']

    qualifying = out[(out['cdsFracStart'] == 0) | (out['cdsFrac'] > 0.25)]
    cds_features = out.groupby('variant').agg(
        cdsFracStartMin=('cdsFracStart', 'min'),
        cdsFracEndMax=('cdsFracEnd', 'max'),
        cdsFracMax=('cdsFrac', 'max'),
    ).join(
        qualifying.groupby('variant').agg(
            pLI_max25_ID=('pLI', 'max'),
            loeuf_min25_ID=('loeuf', 'min'),
        ),
    )
    final = df.merge(cds_features, how='left', left_on='variant', right_index=True)

    final['cdsFracStartMin'].fillna(value=2, inplace=True)
    final['cdsFracEndMax'].fillna(value=-1, inplace=True)
    final['cdsFracMax'].fillna(value=-1, inplace=True)
    final['pLI_max25_ID'].fillna(value=-1, inplace=True)
    final['loeuf_min25_ID'].fillna(value=3, inplace=True)

    usage = read_bed(data_dir, 'summary_exon_usage_hg38.sorted.bed', ['uChrom', 'uStart', 'uStop', 'avgUsage', 'avgExp'])
    usageOverlap = final[['chrom','start','end','variant']].merge(usage, left_on='chrom', right_on='uChrom')
    usageOverlap = usageOverlap[(usageOverlap['start'] < usageOverlap['uStop']) & (usageOverlap['end'] > usageOverlap['uStart'])]
    top_usage = {
        'topUsage': ('avgUsage', lambda x: x.nlargest(size).mean()),
        'topExp': ('avgExp', lambda x: x.nlargest(size).mean()),
    }
    usage_features = usageOverlap.groupby('variant').agg(**top_usage)

    if usage_features.shape[0] == 0:
        usageOverlap = final[['chrom','start','end','variant']].merge(usage, left_on='chrom', right_on='uChrom')
        usageOverlap = usageOverlap[(usageOverlap['start'] - 1000 < usageOverlap['uStop']) & (usageOverlap['end'] + 1000 > usageOverlap['uStart'])]
        usage_features = usageOverlap.groupby('variant').agg(**top_usage)

        if usage_features.shape[0] == 0:
            exp = pd.read_csv(os.path.join(data_dir, 'summary_exon_usage_hg38.sorted.bed'), names=['uChrom', 'uStart', 'uStop','Usage','Exp'],sep='\t')
            usage_features = pd.DataFrame(
                {'topUsage': exp.Usage.median(), 'topExp': exp.Exp.median()},
                index=final['variant'],
            )

    final2 = final.merge(usage_features, how='left', left_on='variant', right_index=True)
    final2['topExp'].fillna(value=final2['topExp'].median(), inplace=True)
    final2['topUsage'].fillna(value=final2['topUsage'].median(), inplace=True)

    return final2


def annotate_strvctvre(svs, data_dir, phylopPath):
    # Implementation of StrVCTVRE: https://github.com/andrewSharo/StrVCTVRE/blob/master/StrVCTVRE.py

    df = svs[['chrom','start','end','svtype']]
    df['variant'] = df.index

    df['length'] = df['end'].astype(int) - df['start'].astype(int)
    df['DEL'] = df['svtype'] == 'DEL'
    df = df[df['length'] > 49]
    df = df[df['DEL'] | (df['svtype'] == 'DUP')]

    exons = read_bed('loading_pipeline/var/strvctre', 'exons_Appris_featurized_transcript_Chr1-Y_loeuf.sorted.bed', ['eChrom', 'eStart', 'eStop', 'gene', 'exonRank', 'skippable', 'exonsInGene', 'const','pLI','loeuf'])
    exonOverlap = df[['chrom','start','end','variant']].merge(exons, left_on='chrom', right_on='eChrom')
    exonOverlap = exonOverlap[(exonOverlap['start'] < exonOverlap['eStop']) & (exonOverlap['end'] > exonOverlap['eStart'])]
    df = df[df['variant'].isin(exonOverlap['variant'])]

    scores = dict.fromkeys(df['variant'], 1.0)

    df = df[df['length'] < 3000000]
    if len(df):
        an = _annotate_sv_features(
            df[['chrom','start','end','variant','DEL']].reset_index(drop=True),
            exonOverlap,
            phylopPath,
            data_dir,
        )

        an['path'] = 0

        rf = load(os.path.join(data_dir, 'rfTrainedAllChromsPy3.joblib'))
        X = an[['DEL','numExonsFinal','phyloP', 'lowestExonRank', 'allSkippable','lowestExonsInGene', 'anyConstExon','pLIMax','loeufMin', 'cdsFracStartMin', 'cdsFracEndMax', 'cdsFracMax', 'pLI_max25_ID', 'loeuf_min25_ID','topExp','topUsage','maxStrength']]
        an['path'] = rf.predict_proba(X)[:,1]
        scores.update({variant: round(path, 3) for variant, path in zip(an['variant'], an['path'])})

    svs['StrVCTVRE'] = svs.index.map(scores.get)

