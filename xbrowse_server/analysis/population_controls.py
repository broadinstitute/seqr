import fisher
from django.conf import settings
from xbrowse.variant_search.cohort import get_individuals_with_inheritance_in_gene
from xbrowse_server.mall import get_reference, get_population_datastore


def control_comparison(gene_id, sample_hits, sample_size, inheritance_mode, variant_filter, quality_filter):
    """
    Compare the results of num_hits, total against the reference population
    Return dict of 'num_hits', 'fisher_2sided_palue',
    """
    cohort = get_population_datastore().get_control_cohort(settings.DEFAULT_CONTROL_COHORT)
    indivs_with_inheritance, gene_variation = get_individuals_with_inheritance_in_gene(
        get_population_datastore(),
        get_reference(),
        cohort,
        inheritance_mode,
        gene_id,
        variant_filter=variant_filter,
        quality_filter=quality_filter
        )
    control_hits = len(indivs_with_inheritance)
    fisher_results = fisher.pvalue(
        sample_hits,
        sample_size,
        control_hits,
        get_population_datastore().get_control_cohort_size(settings.DEFAULT_CONTROL_COHORT)
    )
    return {
        'control_hits': control_hits,
        'fisher_2sided_pvalue': fisher_results.two_tail,
    }