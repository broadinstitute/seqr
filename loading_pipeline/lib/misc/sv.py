import subprocess  # nosec B404

import pandas as pd


def run_command(cmd: list[str]):
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603 # nosec B603
    except subprocess.CalledProcessError as e:
        e.add_note(e.stderr)
        raise


BREAKPOINT_SV_TYPES = ('INS', 'BND', 'CTX')


def match_gnomad_af(variants_df, gnomad_df):
    # Implementation of gatk-sv's AnnotateExternalAFPerShard: https://github.com/broadinstitute/gatk-sv/blob/main/wdl/AnnotateExternalAFPerShard.wdl
    # Changes from base implementation:
    #     - INS / BND multi-candidate selector: replace R2's vestigial col-21 (MID_AF) sort with a deterministic
    #       content-based rule (smallest INS_dis, then |INS_ratio - 1| nearest 0, then lex-smallest ref_svid)
    #     - BND ratio filter dropped: DRAGEN BNDs lack SVLEN; INS_ratio is always None
    #     - CNV tie-break by lex-smallest ref_svid instead of R1's input-order pick

    variants_df['SVLEN:'] = variants_df['SVLEN:'].astype(int)
    variant_is_breakpoint = variants_df['SVTYPE'].isin(BREAKPOINT_SV_TYPES)
    gnomad_is_breakpoint = gnomad_df['SVTYPE'].isin(BREAKPOINT_SV_TYPES)

    matches = pd.concat([
        _best_overlap_matches(variants_df[~variant_is_breakpoint], gnomad_df[~gnomad_is_breakpoint]),
        _best_breakpoint_matches(variants_df[variant_is_breakpoint], gnomad_df[gnomad_is_breakpoint]),
    ])

    af_columns = [c for c in gnomad_df.columns if c not in variants_df.columns]
    return (
        matches.set_index('ID_variant')[['ID_gnomad', *af_columns]]
        .rename(columns={'ID_gnomad': 'id'})
        .to_dict('index')
    )


def _closest_pairs(variants_df, gnomad_df):
    pairs = variants_df.merge(gnomad_df, on=['#CHROM', 'SVTYPE'], suffixes=('_variant', '_gnomad'))
    pairs['distance'] = (pairs['POS_gnomad'] - pairs['END_variant']).clip(
        lower=pairs['POS_variant'] - pairs['END_gnomad'],
    ) + 1
    pairs.loc[pairs['POS_variant'] == pairs['END_variant'], 'distance'] -= 1
    pairs.loc[pairs['POS_gnomad'] == pairs['END_gnomad'], 'distance'] -= 1
    pairs['distance'] = pairs['distance'].clip(lower=0)
    return pairs[pairs['distance'] == pairs.groupby('ID_variant')['distance'].transform('min')]


def _best_overlap_matches(variants_df, gnomad_df):
    pairs = _closest_pairs(
        variants_df.replace({'SVTYPE': {'CPX': 'INV'}}),
        gnomad_df.replace({'SVTYPE': {'CPX': 'INV'}}),
    )
    overlap = pairs['END_variant'].clip(upper=pairs['END_gnomad']) - pairs['POS_variant'].clip(lower=pairs['POS_gnomad'])
    svlen = pairs[['SVLEN_variant', 'SVLEN_gnomad']].max(axis=1, skipna=False)
    pairs = pairs.assign(reciprocal_overlap=(overlap / svlen).where(svlen > 0, 0.0))
    best = pairs.sort_values(
        ['reciprocal_overlap', 'ID_gnomad'],
        ascending=[False, True],
    ).drop_duplicates('ID_variant')
    return best[best['reciprocal_overlap'] > 0.5]


def _best_breakpoint_matches(variants_df, gnomad_df):
    pairs = _closest_pairs(
        variants_df.replace({'SVTYPE': {'CTX': 'BND'}}).assign(
            # Differs from svtk vcf2bed, which uses END rather than a 1bp interval for INS - revisit once using DRAGEN
            END=variants_df['POS'] + 1,
        ),
        gnomad_df.replace({'SVTYPE': {'CTX': 'BND'}}),
    )
    has_svlen = (pairs['SVLEN_gnomad'] > 0) & (pairs['SVLEN_variant'] > 0)
    ins_ratio = (pairs['SVLEN_gnomad'] / pairs['SVLEN_variant']).where(has_svlen)
    pairs['ratio_dist'] = (ins_ratio - 1).abs().fillna(float('inf'))
    pairs['ins_dis'] = (pairs['POS_gnomad'] - pairs['POS_variant']).abs()
    survivors = pairs[
        (pairs['ins_dis'] < 100) &
        ((pairs['SVTYPE'] == 'BND') | ((ins_ratio > 0.1) & (ins_ratio < 10)))
    ]
    return survivors.sort_values(['ins_dis', 'ratio_dist', 'ID_gnomad']).drop_duplicates('ID_variant')
