import subprocess  # nosec B404

import pandas as pd


def run_command(cmd: list[str]):
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603 # nosec B603
    except subprocess.CalledProcessError as e:
        e.add_note(e.stderr)
        raise


BREAKPOINT_SV_TYPES = ('INS', 'BND', 'CTX')


def annotate_gnomad_af(variants_df, gnomad_df):
    variant_is_breakpoint = variants_df['svtype'].isin(BREAKPOINT_SV_TYPES)
    gnomad_is_breakpoint = gnomad_df['svtype'].isin(BREAKPOINT_SV_TYPES)

    matches = pd.concat([
        _best_overlap_matches(variants_df[~variant_is_breakpoint], gnomad_df[~gnomad_is_breakpoint]),
        _best_breakpoint_matches(variants_df[variant_is_breakpoint], gnomad_df[gnomad_is_breakpoint]),
    ])

    af_columns = [c for c in gnomad_df.columns if c not in variants_df.columns]
    matches = matches[['id_variant', 'id_gnomad', *af_columns]].rename(
        columns={'id_variant': 'id', 'id_gnomad': 'gnomad_id'},
    )
    return variants_df.merge(matches, on='id', how='left')


def _closest_pairs(variants_df, gnomad_df):
    pairs = variants_df.merge(gnomad_df, on=['chrom', 'svtype'], suffixes=('_variant', '_gnomad'))
    pairs['distance'] = (pairs['start_gnomad'] - pairs['end_variant']).clip(
        lower=pairs['start_variant'] - pairs['end_gnomad'],
    ) + 1
    pairs.loc[pairs['start_variant'] == pairs['end_variant'], 'distance'] -= 1
    pairs.loc[pairs['start_gnomad'] == pairs['end_gnomad'], 'distance'] -= 1
    pairs['distance'] = pairs['distance'].clip(lower=0)
    return pairs[pairs['distance'] == pairs.groupby('id_variant')['distance'].transform('min')]


def _best_overlap_matches(variants_df, gnomad_df):
    pairs = _closest_pairs(
        variants_df.replace({'svtype': {'CPX': 'INV'}}),
        gnomad_df.replace({'svtype': {'CPX': 'INV'}}),
    )
    overlap = pairs['end_variant'].clip(upper=pairs['end_gnomad']) - pairs['start_variant'].clip(lower=pairs['start_gnomad'])
    svlen = pairs[['svlen_variant', 'svlen_gnomad']].max(axis=1, skipna=False)
    pairs = pairs.assign(reciprocal_overlap=(overlap / svlen).where(svlen > 0, 0.0))
    best = pairs.sort_values(
        ['reciprocal_overlap', 'id_gnomad'],
        ascending=[False, True],
    ).drop_duplicates('id_variant')
    return best[best['reciprocal_overlap'] > 0.5]


def _best_breakpoint_matches(variants_df, gnomad_df):
    pairs = _closest_pairs(
        variants_df.replace({'svtype': {'CTX': 'BND'}}).assign(
            # Differs from svtk vcf2bed, which uses END rather than a 1bp interval for INS - revisit once using DRAGEN
            end=variants_df['start'] + 1,
        ),
        gnomad_df.replace({'svtype': {'CTX': 'BND'}}),
    )
    has_svlen = (pairs['svlen_gnomad'] > 0) & (pairs['svlen_variant'] > 0)
    ins_ratio = (pairs['svlen_gnomad'] / pairs['svlen_variant']).where(has_svlen)
    pairs['ratio_dist'] = (ins_ratio - 1).abs().fillna(float('inf'))
    pairs['ins_dis'] = (pairs['start_gnomad'] - pairs['start_variant']).abs()
    survivors = pairs[
        (pairs['ins_dis'] < 100) &
        (pairs['svtype'] == 'BND') | ((ins_ratio > 0.1) & (ins_ratio < 10))
    ]
    return survivors.sort_values(['ins_dis', 'ratio_dist', 'id_gnomad']).drop_duplicates('id_variant')
