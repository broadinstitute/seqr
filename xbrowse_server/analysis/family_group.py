from django.conf import settings

from xbrowse.variant_search import utils as search_utils
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.mall import get_reference, get_mall


def get_variants_in_gene(family_group, gene_id, variant_filter=None, quality_filter=None):
    """

    """
    variants_by_family = []
    for family in family_group.get_families():
        variant_list = list(get_mall(family.project).variant_store.get_variants_in_gene(
            family.project.project_id,
            family.family_id,
            gene_id,
            variant_filter=variant_filter
        ))
        variant_list = search_utils.filter_gene_variants_by_variant_filter(variant_list, gene_id, variant_filter)
        add_extra_info_to_variants_project(get_reference(), family.project, variant_list, add_family_tags=True, add_populations=True)
        variants_by_family.append({
            'variants': [v.toJSON() for v in variant_list],
            'family_id': family.family_id,
            'project_id': family.project.project_id,
            'family_name': str(family),
        })
    return variants_by_family
