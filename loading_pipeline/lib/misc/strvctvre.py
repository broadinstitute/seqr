import os

import numpy as np
import pandas as pd
import pyBigWig
from joblib import load


def intersect(a, b, window=0):
    a = a.set_axis(range(a.shape[1]), axis=1)
    b = b.set_axis(range(a.shape[1], a.shape[1] + b.shape[1]), axis=1)
    merged = a.merge(b, left_on=0, right_on=a.shape[1])
    return merged[
        (merged[1] - window < merged[a.shape[1] + 2])
        & (merged[2] + window > merged[a.shape[1] + 1])
    ].reset_index(drop=True)


def read_bed(data_dir, file_name):
    return pd.read_csv(os.path.join(data_dir, file_name), sep='\t', header=None)


def topUsage(df,n):
    df['topUsage'] = df.sort_values('avgUsage',ascending=False).iloc[0:n,:]['avgUsage'].mean()
    df['topExp'] = df.sort_values('avgExp',ascending=False).iloc[0:n,:]['avgExp'].mean()
    return df


def cdsRank(df):
    l = df.shape[0]
    dff = df.iloc[0,:]
    if dff['strand'] == 1:
        if dff['start'] - dff['cStart'] < 0:
            df['early'] = dff['cdsCount']
            return df
        else:
            df['early'] = dff['start'] - dff['cStart'] + dff['cdsCount']
            return df
    if dff['strand'] == -1:
        if dff['cStop'] - dff['stop'] < 0:
            df['early'] = dff['cdsCount']
            return df
        else:
            df['early'] = dff['cStop'] - dff['stop'] + dff['cdsCount']
            return df


def cdsEnd(df):
    l = df.shape[0]
    dff = df.iloc[0,:]
    if dff['strand'] == 1:
        if dff['stop'] > dff['cStop']:
            df['late'] = dff['cdsCount'] + dff['size']
            return df
        else:
            df['late'] = dff['stop'] - dff['cStart'] + dff['cdsCount']
            return df
    if dff['strand'] == -1:
        if dff['start'] < dff['cStart']:
            df['late'] = dff['cdsCount'] + dff['size']
            return df
        else:
            df['late'] = dff['cStop'] - dff['start'] + dff['cdsCount']
            return df


def annotateSVs(df, phylopPath, data_dir):

    exons = read_bed(data_dir, 'exons_Appris_featurized_transcript_Chr1-Y_loeuf.sorted.bed')
    df['ID'] = 'sv' + pd.Series(df.index.values).apply(str)
    exonOverlap = intersect(df[['chrom','start','end','ID']], exons).set_axis(
        ['chrom', 'start', 'stop', 'ID', 'eChrom', 'eStart', 'eStop', 'gene', 'exonRank', 'skippable', 'exonsInGene', 'const','pLI','loeuf'], axis=1)
    del exons

    exonOverlap['numExonsFinal'] = exonOverlap.groupby(by='ID').eStart.transform('size')
    exonOverlap['allSkippable'] = exonOverlap.groupby(by='ID').skippable.transform(lambda x: all(x))
    exonOverlap['lowestExonRank'] = exonOverlap.groupby(by='ID').exonRank.transform('min')
    exonOverlap['lowestExonsInGene'] = exonOverlap.groupby(by='ID').exonsInGene.transform('min')
    exonOverlap['anyConstExon'] = exonOverlap.groupby(by='ID').const.transform('max')
    exonOverlap['pLIMax'] = exonOverlap.groupby(by='ID').pLI.transform('max')
    exonOverlap['loeufMin'] = exonOverlap.groupby(by='ID').loeuf.transform('min')

    exonOverlap.drop_duplicates(subset='ID', inplace=True)
    df = df.merge(exonOverlap[['ID', 'numExonsFinal', 'allSkippable', 'lowestExonRank', 'lowestExonsInGene', 'anyConstExon','pLIMax','loeufMin']], how='left', on='ID')
    del exonOverlap

    size = 400

    with open(os.path.join(data_dir, 'hg38chromsizes.tsv')) as f:
        chrms = dict((k, v) for k,v in (line.split() for line in f))

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
    del consBW
    cons = [np.mean(y[np.argsort(y)[-size:]]) for y in x]
    del x
    df['phyloP'] = pd.Series(cons)
    del cons

    tads = read_bed(data_dir, 'rep12tadsMergedhg38.bed')
    tadOverlap = intersect(df[['chrom','start','end','ID']], tads).set_axis(
        ['chrom', 'start', 'stop', 'ID', 'tChrom', 'tStart', 'tStop', 'strength'], axis=1)

    tadOverlap['maxStrength'] = tadOverlap.groupby(by='ID').strength.transform('max')
    tadOverlap.drop_duplicates(subset='ID', inplace=True)
    df = df.merge(tadOverlap[['ID', 'maxStrength']], how='left', on='ID')
    df['maxStrength'].fillna(value=0, inplace=True)
    del tads
    del tadOverlap

    cds = read_bed(data_dir, 'exons_CDS_Chr1-Y.sorted.bed')
    cdsOverlap = intersect(df[['chrom','start','end','ID']], cds).set_axis(
        ['chrom', 'start', 'stop', 'ID', 'cChrom', 'cStart', 'cStop', 'CDSLength', 'size', 'exonRank', 'strand','gene', 'cdsCount', 'pLI','loeuf'], axis=1)
    del cds
    if cdsOverlap.shape[0] != 0:
        out = cdsOverlap.sort_values('exonRank').groupby(['ID','gene']).apply(cdsRank)
        out.reset_index(drop=True, inplace=True)
        out = out.sort_values('exonRank', ascending=False).groupby(['ID','gene']).apply(cdsEnd)

        out.drop_duplicates(subset='ID').shape[0]

        out['cdsFracStart'] = out['early']/out['CDSLength']
        out['cdsFracEnd'] = out['late']/out['CDSLength']
        out['cdsFrac'] = (out['late'] - out['early'])/out['CDSLength']

        out.reset_index(drop=True, inplace=True)
        out['pLI_max25'] = out[(out['cdsFracStart'] == 0) | (out['cdsFrac'] > 0.25)].groupby('ID')['pLI'].transform('max')
        out.reset_index(drop=True, inplace=True)
        out['loeuf_min25']= out[(out['cdsFracStart'] == 0) | (out['cdsFrac'] > 0.25)].groupby('ID')['loeuf'].transform('min')
        out.reset_index(drop=True, inplace=True)

        out['pLI_max25_ID'] = out.groupby('ID')['pLI_max25'].transform('max')
        out.reset_index(drop=True, inplace=True)
        out['loeuf_min25_ID'] = out.groupby('ID')['loeuf_min25'].transform('max')
        out.reset_index(drop=True, inplace=True)
        out['cdsFracMax'] = out.groupby('ID')['cdsFrac'].transform('max')
        out.reset_index(drop=True, inplace=True)
        out['cdsFracStartMin'] = out.groupby('ID')['cdsFracStart'].transform('min')
        out.reset_index(drop=True, inplace=True)
        out['cdsFracEndMax'] = out.groupby('ID')['cdsFracEnd'].transform('max')
        out.reset_index(drop=True, inplace=True)
        out.drop_duplicates(subset='ID', inplace=True)

        final = df.merge(out[['ID', 'cdsFracStartMin', 'cdsFracEndMax', 'cdsFracMax', 'pLI_max25_ID', 'loeuf_min25_ID']], how='left')
        del out
    else:
        final = df.copy()
        del df
        final['cdsFracStartMin'] = float('NaN')
        final['cdsFracEndMax'] = float('NaN')
        final['cdsFracMax'] = float('NaN')
        final['pLI_max25_ID'] = float('NaN')
        final['loeuf_min25_ID'] = float('NaN')

    del cdsOverlap
    final['cdsFracStartMin'].fillna(value=2, inplace=True)
    final['cdsFracEndMax'].fillna(value=-1, inplace=True)
    final['cdsFracMax'].fillna(value=-1, inplace=True)
    final['pLI_max25_ID'].fillna(value=-1, inplace=True)
    final['loeuf_min25_ID'].fillna(value=3, inplace=True)

    usage = read_bed(data_dir, 'summary_exon_usage_hg38.sorted.bed')
    usageOverlap = intersect(final[['chrom','start','end','ID']], usage).set_axis(
        ['chrom', 'start', 'stop', 'ID', 'uChrom', 'uStart', 'uStop', 'avgUsage', 'avgExp'], axis=1)
    out = usageOverlap.groupby('ID').apply(topUsage,n=size)
    out.drop_duplicates(subset='ID', inplace=True)

    if out.shape[0] == 0:
        usageOverlap = intersect(final[['chrom','start','end','ID']], usage, window=1000).set_axis(
            ['chrom', 'start', 'stop', 'ID', 'uChrom', 'uStart', 'uStop', 'avgUsage', 'avgExp'], axis=1)
        pd.read_csv(os.path.join(data_dir, 'summary_exon_usage_hg38.sorted.bed'))
        out = usageOverlap.groupby('ID').apply(topUsage,n=size)
        out.drop_duplicates(subset='ID', inplace=True)

        if out.shape[0] == 0:
            exp = pd.read_csv(os.path.join(data_dir, 'summary_exon_usage_hg38.sorted.bed'), names=['uChrom', 'uStart', 'uStop','Usage','Exp'],sep='\t')
            usageMed = exp.Usage.median()
            expMed = exp.Exp.median()
            out = final[['ID']].copy()
            out['topUsage'] = usageMed
            out['topExp'] = expMed

    out.reset_index(drop=True, inplace=True)
    final2 = final.merge(out[['ID', 'topUsage', 'topExp']], how='left', on='ID')
    del final
    del out
    final2['topExp'].fillna(value=final2['topExp'].median(), inplace=True)
    final2['topUsage'].fillna(value=final2['topUsage'].median(), inplace=True)

    return final2


def annotate_strvctvre(svs, data_dir, phylopPath):
    has_end_and_svtype = svs['end'].notna() & svs['svtype'].notna()
    df = svs[has_end_and_svtype][['chrom','start','end','svtype']].reset_index(drop=True)

    if df.shape[0] == 0:
        return svs.assign(StrVCTVRE=None)

    df['OldID'] = pd.Series(df.index.values)

    if sum(df['chrom'].astype(str).str.startswith('chr',na=False))/df.shape[0] < 0.5:
        df['chrom'] = 'chr' + df['chrom'].astype(str)

    acceptedChroms = ['chr1','chr2','chr3','chr4','chr5','chr6','chr7','chr8','chr9','chr10','chr11','chr12','chr13',
                     'chr14','chr15','chr16','chr17','chr18','chr19','chr20','chr21','chr22','chrX','chrY']
    df = df[df['chrom'].isin(acceptedChroms)].copy()
    validChrom = df.copy()
    validChrom['validChrom'] = True

    df = df[pd.to_numeric(df['start'], errors='coerce').notnull()].copy()
    df = df[pd.to_numeric(df['end'], errors='coerce').notnull()].copy()
    df['start'] = df['start'].astype(float)
    df['end'] = df['end'].astype(float)
    df = df[df['start'] == df['start'] // 1]
    df = df[df['end'] == df['end'] // 1]
    df['start'] = df['start'].astype(int)
    df['end'] = df['end'].astype(int)
    validStartEnd = df.copy()

    df['length'] = df['end'].astype(int) - df['start'].astype(int)
    df = df[df['length'] > 49].copy()
    validLength = df.copy()
    validLength['validLength'] = True

    df = df[((df['svtype'] == 'DEL') | (df['svtype'] == 'DUP'))].copy()
    validSVType = df.copy()
    validSVType['validSVType'] = True
    df['DEL'] = df['svtype'] == 'DEL'

    exons = read_bed(data_dir, 'exons_Appris_featurized_transcript_Chr1-Y_loeuf.sorted.bed')
    exonOverlap = intersect(df[['chrom','start','end','OldID']], exons).iloc[:, [0,1,2,3]].set_axis(
        ['chrom', 'start', 'stop', 'OldID'], axis=1)
    exonOverlap['numExons'] = exonOverlap.groupby(by='OldID').chrom.transform('size')
    exonOverlap.drop_duplicates(subset='OldID', inplace=True)

    del exons

    out = df.merge(exonOverlap[['numExons','OldID']],how='left',on='OldID')
    del exonOverlap
    del df
    out = out[out['numExons'] > 0]
    validExon = out.set_index('OldID').copy()
    validExon['validExon'] = True
    out = out[out['length'] < 3000000]

    if out.shape[0] != 0:
        an = annotateSVs(out[['chrom','start','end','OldID','DEL']].reset_index(drop=True), phylopPath, data_dir)
        del out

        an['path'] = 0

        rf = load(os.path.join(data_dir, 'rfTrainedAllChromsPy3.joblib'))
        X = an[['DEL','numExonsFinal','phyloP', 'lowestExonRank', 'allSkippable','lowestExonsInGene', 'anyConstExon','pLIMax','loeufMin', 'cdsFracStartMin', 'cdsFracEndMax', 'cdsFracMax', 'pLI_max25_ID', 'loeuf_min25_ID','topExp','topUsage','maxStrength']].copy()
        an['path'] = rf.predict_proba(X)[:,1]
        an.set_index('OldID', inplace=True)
    else:
        an = pd.DataFrame()

    scores = []
    count = 0
    for valid in has_end_and_svtype:
        if valid:
            if count in an.index:
                scores.append(str(round(an.loc[count,'path'],3)))
            elif count in validExon.index:
                scores.append('1.0')
            elif count in validSVType.index:
                scores.append('not_exonic')
            elif count in validLength.index:
                scores.append('not_dup_or_del')
            elif count in validStartEnd.index:
                scores.append('less_than_50bp')
            elif count in validChrom.index:
                scores.append('invalid_start_or_end')
            else:
                scores.append('not_valid_chrom')
            count += 1
        else:
            scores.append('missing_END_or_SVTYPE')
    return svs.assign(StrVCTVRE=scores)
