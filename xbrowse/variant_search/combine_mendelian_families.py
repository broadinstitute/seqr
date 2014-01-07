from .family import get_variants_with_inheritance_mode
from xbrowse.core.variant_filters import VariantFilter
from xbrowse.core.inheritance import inheritance_makes_sense_for_family

from collections import defaultdict


def get_families_by_gene(datastore, reference, family_group, inheritance_mode, variant_filter=None, quality_filter=None):

    families_by_gene = defaultdict(set)

    for family in family_group.get_families():
        for variant in get_variants_with_inheritance_mode(
                datastore,
                reference,
                family,
                inheritance_mode,
                variant_filter,
                quality_filter
        ):
            for gene_id in variant.coding_gene_ids:
                families_by_gene[gene_id].add((family.project_id, family.family_id))

    for gene_id, family_set in families_by_gene.items():
        yield gene_id, sorted(list(family_set))


def get_variants_by_family_for_gene(datastore, reference, family_list, inheritance_mode, gene_id, variant_filter=None, quality_filter=None):

    if variant_filter is None:
        variant_filter = VariantFilter()
    variant_filter.add_gene(gene_id)

    by_family = {}
    for family in family_list:
        family_t = (family.project_id, family.family_id)
        variants = list(get_variants_with_inheritance_mode(
            datastore,
            reference,
            family,
            inheritance_mode,
            variant_filter,
            quality_filter
        ))
        by_family[family_t] = variants

    return by_family


def get_family_matrix_for_gene(datastore, reference, family_list, gene_id, variant_filter=None, quality_filter=None):
    """
    Same as above, but run for each inheritance mode of recessive, dominant, denovo
    Only run an inheritance mode if it makes sense for that family
    """
    ret = {}
    for inheritance_mode in ['dominant', 'recessive', 'de_novo']:
        families = [f for f in family_list if inheritance_makes_sense_for_family(f, inheritance_mode)]
        family_variants = get_variants_by_family_for_gene(
            datastore,
            reference,
            families,
            inheritance_mode,
            gene_id,
            variant_filter,
            quality_filter
        )
        ret[inheritance_mode] = {family_tuple: variants for family_tuple, variants in family_variants.items() if len(variants) > 0}

    return ret