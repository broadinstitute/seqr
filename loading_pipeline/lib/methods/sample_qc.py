import hail as hl
import onnx
from gnomad.sample_qc.ancestry import (
    apply_onnx_classification_model,
    assign_population_pcs,
    pc_project,
)
from gnomad.sample_qc.filtering import compute_stratified_metrics_filter
from gnomad.sample_qc.pipeline import filter_rows_for_qc
from gnomad.utils.filtering import filter_to_autosomes
from gnomad_qc.v4.sample_qc.assign_ancestry import assign_pop_with_per_pop_probs

from loading_pipeline.lib.core import SampleType

GNOMAD_FILTER_MIN_AF = 0.001
GNOMAD_FILTER_MIN_CALLRATE = 0.99

CALLRATE_LOW_THRESHOLD = 0.85
CONTAMINATION_UPPER_THRESHOLD = 0.05
WES_COVERAGE_LOW_THRESHOLD = 85
WGS_CALLRATE_LOW_THRESHOLD = 30

NUM_PCS = 20
GNOMAD_POP_PROBABILITY_CUTOFFS = {
    'afr': 0.93,
    'ami': 0.98,
    'amr': 0.89,
    'asj': 0.94,
    'eas': 0.95,
    'fin': 0.92,
    'mid': 0.55,
    'nfe': 0.75,
    'sas': 0.92,
}
POPULATION_MISSING_LABEL = 'oth'
HAIL_QC_METRICS = [
    'n_snp',
    'r_ti_tv',
    'r_insertion_deletion',
    'n_insertion',
    'n_deletion',
    'r_het_hom_var',
]


def call_sample_qc(
    mt: hl.MatrixTable,
    tdr_metrics_ht: hl.Table,
    pop_pca_loadings_ht: hl.Table,
    ancestry_rf_model: onnx.ModelProto,
    sample_type: SampleType,
):
    mt = mt.annotate_entries(
        GT=hl.case()
        .when(mt.GT.is_diploid(), hl.call(mt.GT[0], mt.GT[1], phased=False))
        .when(mt.GT.is_haploid(), hl.call(mt.GT[0], phased=False))
        .default(hl.missing(hl.tcall)),
    )
    mt = annotate_filtered_callrate(mt)
    # Annotates contamination_rate, percent_bases_at_20x, and mean_coverage
    mt = mt.annotate_cols(**tdr_metrics_ht[mt.col_key])
    mt = annotate_filter_flags(mt, sample_type)
    mt = annotate_qc_gen_anc(mt, pop_pca_loadings_ht, ancestry_rf_model)
    return run_hail_sample_qc(mt, sample_type)


def annotate_filtered_callrate(mt: hl.MatrixTable) -> hl.MatrixTable:
    filtered_mt = filter_rows_for_qc(
        mt,
        min_af=GNOMAD_FILTER_MIN_AF,
        min_callrate=GNOMAD_FILTER_MIN_CALLRATE,
        bi_allelic_only=True,
        snv_only=True,
        apply_hard_filters=False,
        min_inbreeding_coeff_threshold=None,
        min_hardy_weinberg_threshold=None,
    )
    callrate_ht = filtered_mt.select_cols(
        filtered_callrate=hl.agg.fraction(hl.is_defined(filtered_mt.GT)),
    ).cols()
    return mt.annotate_cols(**callrate_ht[mt.col_key])


def annotate_filter_flags(
    mt: hl.MatrixTable,
    sample_type: SampleType,
) -> hl.MatrixTable:
    flags = {
        'callrate': mt.filtered_callrate < CALLRATE_LOW_THRESHOLD,
        'contamination': mt.contamination_rate > CONTAMINATION_UPPER_THRESHOLD,
        'coverage': (
            mt.percent_bases_at_20x < WES_COVERAGE_LOW_THRESHOLD
            if sample_type == SampleType.WES
            else mt.mean_coverage < WGS_CALLRATE_LOW_THRESHOLD
        ),
    }
    return mt.annotate_cols(
        filter_flags=hl.array(
            [hl.or_missing(filter_cond, name) for name, filter_cond in flags.items()],
        ).filter(hl.is_defined),
    )


def annotate_qc_gen_anc(
    mt: hl.MatrixTable,
    pop_pca_loadings_ht: hl.Table,
    ancestry_rf_model: onnx.ModelProto,
) -> hl.MatrixTable:
    mt = mt.select_entries('GT')
    scores = pc_project(mt, pop_pca_loadings_ht)
    scores = scores.annotate(scores=scores.scores[:NUM_PCS], known_pop='Unknown')
    pop_pca_ht, _ = assign_population_pcs(
        scores,
        pc_cols=scores.scores,
        output_col='qc_pop',
        fit=ancestry_rf_model,
        apply_model_func=apply_onnx_classification_model,
    )
    pop_pca_ht = pop_pca_ht.key_by('s')
    scores = scores.annotate(
        **{f'pop_PC{i + 1}': scores.scores[i] for i in range(NUM_PCS)},
    ).drop('scores', 'known_pop')
    pop_pca_ht = pop_pca_ht.annotate(**scores[pop_pca_ht.key])
    pop_pca_ht = assign_pop_with_per_pop_probs(
        pop_pca_ht,
        min_prob_cutoffs=GNOMAD_POP_PROBABILITY_CUTOFFS,
        missing_label=POPULATION_MISSING_LABEL,
    )
    pop_pca_ht = pop_pca_ht.transmute(qc_gen_anc=pop_pca_ht.pop).drop('qc_pop')
    return mt.annotate_cols(**pop_pca_ht[mt.col_key])


def run_hail_sample_qc(mt: hl.MatrixTable, sample_type: SampleType) -> hl.MatrixTable:
    mt = filter_to_autosomes(mt)
    mt = hl.sample_qc(mt)
    mt = mt.annotate_cols(
        sample_qc=mt.sample_qc.annotate(
            f_inbreeding=hl.agg.inbreeding(mt.GT, mt['info.AF'][0]),
        ),
    )
    sample_qc_metrics = HAIL_QC_METRICS
    if sample_type == SampleType.WGS:
        sample_qc_metrics = [*sample_qc_metrics, 'call_rate']

    strat_ht = mt.cols()
    qc_metrics = {metric: strat_ht.sample_qc[metric] for metric in sample_qc_metrics}
    strata = {'qc_gen_anc': strat_ht.qc_gen_anc}

    metric_ht = compute_stratified_metrics_filter(strat_ht, qc_metrics, strata)
    metric_ht = metric_ht.annotate(
        sample_qc=mt.cols()[metric_ht.key].sample_qc,
        qc_metrics_filters=hl.array(metric_ht.qc_metrics_filters),
    )
    return mt.annotate_cols(**metric_ht[mt.col_key])
