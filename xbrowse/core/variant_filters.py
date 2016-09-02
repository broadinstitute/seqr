import copy
from collections import namedtuple
import sys
from xbrowse.core import genomeloc

class VariantFilter(object):
    """
    Used to describe variants of interest
    """
    def __init__(self, **kwargs):
        self.variant_types = kwargs.get('variant_types')
        self.so_annotations = kwargs.get('so_annotations')  # todo: rename (and refactor)
        self.annotations = kwargs.get('annotations', {})
        self.ref_freqs = kwargs.get('ref_freqs')
        self.locations = kwargs.get('locations')
        self.genes = kwargs.get('genes')

    def toJSON(self):
        d = {}
        for key in ['variant_types', 'so_annotations', 'ref_freqs', 'annotations', 'genes']:
            if getattr(self, key):
                d[key] = getattr(self, key)
        if getattr(self, 'locations'):
            d['locations'] = ["%s:%s-%s" % (genomeloc.get_chr_pos(locA)[0], genomeloc.get_chr_pos(locA)[1], genomeloc.get_chr_pos(locB)[1]) for locA, locB in self.locations]
        return d

    @classmethod
    def fromJSON(self, d):
        vf = VariantFilter(**d)
        return vf

    def add_gene(self, gene_id):
        if self.genes is None:
            self.genes = []
        self.genes.append(gene_id)


DEFAULT_VARIANT_FILTERS = [
    {
        'slug': 'high_impact', 
        'name': 'High Impact', 
        'description': '', 
        'variant_filter': VariantFilter(
            so_annotations=[
                'stop_gained',
                'splice_donor_variant',
                'splice_acceptor_variant',
                'frameshift_variant',
            ],
        )
    },
    {
        'slug': 'moderate_impact', 
        'name': 'Moderate to High Impact', 
        'description': '',
        'variant_filter': VariantFilter(
            so_annotations=[
                'stop_gained',
                'splice_donor_variant',
                'splice_acceptor_variant',
                'frameshift_variant',
                'stop_lost',
                'initiator_codon_variant',
                'start_lost',
                'missense_variant',
                'inframe_insertion',
                'inframe_deletion',
                'protein_altering_variant',
            ],
        ),
    },
    {
        'slug': 'all_coding', 
        'name': 'All rare coding variants', 
        'description': '',
        'variant_filter': VariantFilter(
            so_annotations=[
                'stop_gained',
                'splice_donor_variant',
                'splice_acceptor_variant',
                'splice_region_variant',
                'stop_lost',
                'initiator_codon_variant',
                'start_lost',
                'missense_variant',
                'frameshift_variant',
                'inframe_insertion',
                'inframe_deletion',
                'protein_altering_variant',
                'synonymous_variant',
                'stop_retained_variant',
                'splice_region_variant',
            ],
        ),
    },
]

DEFAULT_VARIANT_FILTERS_DICT = {item['slug']: item for item in DEFAULT_VARIANT_FILTERS}


def get_default_variant_filters(reference_population_slugs=None):
    full_filters = copy.deepcopy(DEFAULT_VARIANT_FILTERS)
    for f in full_filters:
        f['variant_filter'] = get_default_variant_filter(f['slug'], reference_population_slugs)
    return full_filters


def get_default_variant_filter(slug, reference_population_slugs=None):
    if reference_population_slugs is None:
        ref_freqs = []
    else:
        ref_freqs = [(s, .01) for s in reference_population_slugs]
    if slug in DEFAULT_VARIANT_FILTERS_DICT:
        variant_filter = copy.deepcopy(DEFAULT_VARIANT_FILTERS_DICT[slug]['variant_filter'])
        variant_filter.ref_freqs = ref_freqs
        return variant_filter
    else:
        return None


def passes_variant_filter_basics(variant, variant_filter):
    """
    Basic variant filters: vartypes, so_annotations,
    """

    if variant_filter.variant_types:
        if variant.vartype not in variant_filter.variant_types:
            return False, 'variant_types'

    if variant_filter.so_annotations:
        if variant.annotation['vep_consequence'] not in variant_filter.so_annotations:
            return False, 'so_annotations'

    if variant_filter.locations:
        passed = False
        for xstart, xstop in variant_filter.locations:
            if variant.xposx >= xstart and variant.xpos <= xstop:
                passed = True
                break
        if not passed:
            return False, 'location'

    if variant_filter.genes:
        if not (set(variant_filter.genes) & set(variant.gene_ids)):
            return False, "genes"

    return True, None


def passes_variant_filter(variant, variant_filter):
    """
    See if variant passes variant filter
    Return (success, result)
    if success, result is None; else is the name of the field that failed filter

    ***Note*** - takes a namedtuple, I want to switch variant filters to this across the code

    """

    success, result = passes_variant_filter_basics(variant, variant_filter)
    if not success:
        return success, result

    if variant_filter.ref_freqs:
        for population, freq in variant_filter.ref_freqs:
            try:
                if variant.annotation['freqs'][population] > freq:
                    return False, 'max_af'
            except Exception, e:
                sys.stderr.write("Error while checking if %(population)s > %(freq)s\n" % locals())

    if variant_filter.annotations:
        for key, annot_list in variant_filter.annotations.items():
            if variant.annotation.get(key) not in annot_list:
                return False, key

    return True, None


_AlleleCountFilter = namedtuple('AlleleCountFilter', [
    # int; include variants with at least this many copies of the alt allele
    # in practice, this filter works by filtering out variants with < N copies, but xbrowse filters are inclusive
    'affected_gte',
    'affected_lte',
    'unaffected_gte',
    'unaffected_lte',
])
_default_allelecountfilter = _AlleleCountFilter(None, None, None, None)


def AlleleCountFilter(**kwargs):
    return _default_allelecountfilter._replace(**kwargs)


def passes_allele_count_filter(variant, allele_count_filter, affected_status_map):
    """
    Does variant pass allele count filter?
    Args:
        affected_status_map: dict of indiv_id -> affected status
    """
    affected_aac = 0
    unaffected_aac = 0
    for indiv_id, genotype in variant.get_genotypes():
        if genotype.num_alt is not None:
            if affected_status_map[indiv_id] == 'affected':
                affected_aac += genotype.num_alt
            elif affected_status_map[indiv_id] == 'unaffected':
                unaffected_aac += genotype.num_alt
    if allele_count_filter.affected_gte is not None and affected_aac < allele_count_filter.affected_gte:
        return False
    if allele_count_filter.affected_lte is not None and affected_aac > allele_count_filter.affected_lte:
        return False
    if allele_count_filter.unaffected_gte is not None and unaffected_aac < allele_count_filter.unaffected_gte:
        return False
    if allele_count_filter.unaffected_lte is not None and unaffected_aac > allele_count_filter.unaffected_lte:
        return False
    return True
