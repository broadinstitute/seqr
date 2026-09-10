import hail as hl

from loading_pipeline.lib.core import Sex

AMBIGUOUS_THRESHOLD_PERC: float = 0.01  # Fraction of samples identified as "ambiguous_sex" above which an error will be thrown.
AAF_THRESHOLD: float = 0.05  # Alternate allele frequency threshold for `hl.impute_sex`.
BIALLELIC: int = 2
XX_FSTAT_THRESHOLD: float = (
    0.5  # F-stat threshold below which a sample will be called XX
)
XY_FSTAT_THRESHOLD: float = (
    0.75  # F-stat threshold above which a sample will be called XY.
)


def compute_sex_check_ht(mt: hl.MatrixTable) -> hl.Table:
    # Filter to SNVs and biallelics
    # NB: We should already have filtered biallelics, but just in case.
    mt = mt.filter_rows(
        (hl.len(mt.alleles) == BIALLELIC) & hl.is_snp(mt.alleles[0], mt.alleles[1]),
    )
    mt = mt.filter_cols(hl.agg.all(mt.GT.is_diploid() | hl.is_missing(mt.GT)))

    # Filter to PASS variants only (variants with empty or missing filter set)
    mt = mt.filter_rows(
        hl.is_missing(mt.filters) | (mt.filters.length() == 0),
        keep=True,
    )
    impute_sex_ht = hl.impute_sex(
        mt.GT,
        male_threshold=XY_FSTAT_THRESHOLD,
        female_threshold=XX_FSTAT_THRESHOLD,
        aaf_threshold=AAF_THRESHOLD,
    )
    ht = mt.annotate_cols(**impute_sex_ht[mt.col_key]).cols()
    ht = ht.select(
        predicted_sex=(
            hl.case()
            .when(hl.is_missing(ht.is_female), Sex.UNKNOWN.value)
            .when(ht.is_female, Sex.FEMALE.value)
            .default(Sex.MALE.value)
        ),
    )
    ambiguous_perc = ht.aggregate(
        hl.agg.fraction(ht.predicted_sex == Sex.UNKNOWN.value),
    )
    if ambiguous_perc > AMBIGUOUS_THRESHOLD_PERC:
        msg = f'{ambiguous_perc:.2%} of samples identified as ambiguous.  Please contact the methods team to investigate the callset.'
        raise ValueError(msg)
    return ht
