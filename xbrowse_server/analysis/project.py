from django.conf import settings
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse.core.quality_filters import get_default_quality_filter
from xbrowse.variant_search import utils as search_utils
from xbrowse.variant_search.cohort import CohortGeneVariation, get_individuals_with_inheritance
from xbrowse_server import mall
from xbrowse_server.mall import get_reference, get_mall, get_project_datastore


def get_variants_in_gene(project, gene_id, variant_filter=None, quality_filter=None):
    """
    Get all the variants in a gene, but filter out quality_filter genotypes
    """
    variant_list = get_project_datastore(project).get_project_variants_in_gene(project.project_id, gene_id, variant_filter=variant_filter)
    variant_list = search_utils.filter_gene_variants_by_variant_filter(variant_list, gene_id, variant_filter)
    return variant_list


def get_knockouts_in_gene(project, gene_id, gene_variants):
    """
    Get all the variants in a gene, but filter out quality_filter genotypes
    """
    indiv_id_list = [i.indiv_id for i in project.get_individuals()]

    # filter out variants > 0.01 AF in any of the reference populations
    reference_populations = mall.get_annotator().reference_population_slugs
    variant_filter = get_default_variant_filter('moderate_impact', reference_populations)
    variant_list = search_utils.filter_gene_variants_by_variant_filter(gene_variants, gene_id, variant_filter)

    variation = CohortGeneVariation(
        get_reference(),
        gene_id,
        variant_list,
        indiv_id_list,
        quality_filter={},
    )
    knockouts = get_individuals_with_inheritance('recessive', variation, indiv_id_list)
    return knockouts, variation
