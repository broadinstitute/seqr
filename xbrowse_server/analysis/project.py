from django.conf import settings
from xbrowse.analysis_modules.combine_mendelian_families import get_family_matrix_for_gene
from xbrowse.core.variant_filters import get_default_variant_filter
from xbrowse.core.quality_filters import get_default_quality_filter
from xbrowse.variant_search import utils as search_utils
from xbrowse.variant_search.cohort import CohortGeneVariation, get_individuals_with_inheritance


def inheritance_matrix_for_gene(project, gene_id):
    """
    Run get_family_matrix_for_gene for the families in this project
    """
    variant_filter = get_default_variant_filter('moderate_impact', settings.ANNOTATOR.reference_population_slugs)
    quality_filter = get_default_quality_filter('high_quality', settings.ANNOTATOR.reference_population_slugs)
    matrix = get_family_matrix_for_gene(
        settings.DATASTORE,
        settings.REFERENCE,
        [f.xfamily() for f in project.get_active_families()],
        gene_id,
        variant_filter,
        quality_filter
    )
    return matrix


def get_variants_in_gene(project, gene_id, variant_filter=None, quality_filter=None):
    """
    Get all the variants in a gene, but filter out quality_filter genotypes
    """
    variant_list = settings.PROJECT_DATASTORE.get_variants_in_gene(project.project_id, gene_id, variant_filter=variant_filter)
    variant_list = search_utils.filter_gene_variants_by_variant_filter(variant_list, gene_id, variant_filter)
    return variant_list


def get_knockouts_in_gene(project, gene_id, quality_filter=None):
    """
    Get all the variants in a gene, but filter out quality_filter genotypes
    """
    indiv_id_list = [i.indiv_id for i in project.get_individuals()]
    variant_filter = get_default_variant_filter('high_impact')
    variant_list = settings.PROJECT_DATASTORE.get_variants_in_gene(
        project.project_id,
        gene_id,
        variant_filter=variant_filter,
    )
    variant_list = search_utils.filter_gene_variants_by_variant_filter(variant_list, gene_id, variant_filter)
    variation = CohortGeneVariation(
        settings.REFERENCE,
        gene_id,
        variant_list,
        indiv_id_list,
        quality_filter={},
    )
    knockouts = get_individuals_with_inheritance('recessive', variation, indiv_id_list)
    return knockouts, variation
