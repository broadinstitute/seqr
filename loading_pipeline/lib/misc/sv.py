import subprocess  # nosec B404

import numpy as np
import pandas as pd


def run_command(cmd: list[str]):
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603 # nosec B603
    except subprocess.CalledProcessError as e:
        e.add_note(e.stderr)
        raise


SV_TYPE_GROUP_OVERRIDES = {'CPX': 'INV', 'CTX': 'BND'}
OVERLAP_SV_TYPE_GROUPS = ('DEL', 'DUP', 'INV')


def _closest_pairs(variants_df, gnomad_df):
    pairs = variants_df.merge(gnomad_df, on=['chrom', 'sv_type_group'], suffixes=('_query', '_ref'))
    query_zero_length = pairs['start_query'] == pairs['end_query']
    ref_zero_length = pairs['start_ref'] == pairs['end_ref']
    query_start = pairs['start_query'] - query_zero_length
    query_end = pairs['end_query'] + query_zero_length
    ref_start = pairs['start_ref'] - ref_zero_length
    ref_end = pairs['end_ref'] + ref_zero_length
    overlaps = (ref_start < query_end) & (query_start < ref_end)
    gap = np.maximum(ref_start - query_end, query_start - ref_end) + 1
    pairs['distance'] = gap.where(~overlaps, 0)
    return pairs[pairs['distance'] == pairs.groupby('id_query')['distance'].transform('min')]


def _best_overlap_matches(pairs):
    overlap = np.minimum(pairs['end_query'], pairs['end_ref']) - np.maximum(pairs['start_query'], pairs['start_ref'])
    denom = np.maximum(pairs['svlen_query'], pairs['svlen_ref'])
    pairs = pairs.assign(ro=(overlap / denom).where(denom > 0, 0.0))
    best = pairs.sort_values(['ro', 'id_ref'], ascending=[False, True]).drop_duplicates('id_query')
    return best[best['ro'] > 0.5]


def _best_breakpoint_matches(pairs):
    ins_dis = (pairs['start_ref'] - pairs['start_query']).abs()
    has_svlen = (pairs['svlen_ref'] > 0) & (pairs['svlen_query'] > 0)
    ins_ratio = (pairs['svlen_ref'] / pairs['svlen_query']).where(has_svlen)
    pairs = pairs.assign(ins_dis=ins_dis, ratio_dist=(ins_ratio - 1).abs().fillna(np.inf))
    ratio_ok = (pairs['sv_type_group'] == 'BND') | ((ins_ratio > 0.1) & (ins_ratio < 10))
    survivors = pairs[(ins_dis < 100) & ratio_ok]
    return survivors.sort_values(['ins_dis', 'ratio_dist', 'id_ref']).drop_duplicates('id_query')


def _query_intervals(variants_df):
    is_cnv = variants_df['svtype'] == 'CNV'
    sv_type_group = variants_df['svtype'].replace(SV_TYPE_GROUP_OVERRIDES).mask(is_cnv, variants_df['alt'].str.strip('<>'))
    df = variants_df.assign(sv_type_group=sv_type_group)
    is_overlap_group = df['sv_type_group'].isin(OVERLAP_SV_TYPE_GROUPS)
    return df.assign(start=df['pos'] - 1, end=df['end'].where(is_overlap_group, df['pos']))


def annotate_external_af(variants_df, gnomad_df):
    af_columns = [c for c in gnomad_df.columns if c not in ('chrom', 'start', 'end', 'id', 'svtype', 'svlen')]
    pairs = _closest_pairs(
        _query_intervals(variants_df),
        gnomad_df.assign(sv_type_group=gnomad_df['svtype'].replace(SV_TYPE_GROUP_OVERRIDES)),
    )
    is_overlap_group = pairs['sv_type_group'].isin(OVERLAP_SV_TYPE_GROUPS)
    matches = pd.concat([
        _best_overlap_matches(pairs[is_overlap_group]),
        _best_breakpoint_matches(pairs[~is_overlap_group]),
    ])
    matches = matches[['id_query', 'id_ref', *af_columns]].rename(
        columns={'id_query': 'id', 'id_ref': 'gnomad_id'},
    )
    return variants_df.merge(matches, on='id', how='left')
