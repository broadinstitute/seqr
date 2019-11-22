"""
Methods for getting variants in a cohort
TODO: this file should probably only contain search methods; 
extract the utilities to a cohort_variants or something
"""
from collections import defaultdict

from xbrowse.core.genotype_filters import passes_genotype_filter
from xbrowse import stream_utils
from xbrowse import genomeloc
from xbrowse.variant_search import utils as search_utils


def get_quality_filtered_genotypes(variant, quality_filter):
    """
    Returns:
        A list of (indiv_id, genotype) tuples for genotypes that pass quality filter, or an empty list if none do
    """
    ret = []
    num_het = 0
    num_hom_alt = 0
    num_genotypes = variant.num_genotypes()
    for indiv_id, genotype in variant.get_genotypes():
        if genotype.num_alt > 0:
            if passes_genotype_filter(genotype, quality_filter):
                if genotype.num_alt == 1:
                    num_het += 1
                if genotype.num_alt == 2:
                    num_hom_alt += 1
                ret.append((indiv_id, genotype))

    if 'het_ratio' in quality_filter:
        if float(num_het)*100 / num_genotypes > quality_filter['het_ratio']:
            return []

    if 'hom_alt_ratio' in quality_filter:
        if float(num_hom_alt)*100 / num_genotypes > quality_filter['hom_alt_ratio']:
            return []

    return ret


class CohortGeneVariation:
    """
    Represents the variation in a gene across an arbitrary cohort of individuals
    """
    def __init__(self, reference, gene_id, variant_list, indiv_ids, quality_filter=None):
        """
        variants is an iterator of Variants
        indiv_ids is a list of indiv_ids for the individuals in this cohort
        Not all indiv_ids have to have genotypes in all (or any) variants
        """
        self.reference = reference
        self.gene_id = gene_id
        self.variants = variant_list
        self.indiv_ids = indiv_ids
        self.quality_filter = quality_filter
        self._index()

    def _index(self):
        """
        Set up lookup indices - must be called before any getters
        """
        self.indiv_genotypes = defaultdict(list)  # map of indiv_id -> genotype_list
        num_variants = self.num_variants()

        # map of indiv_id -> list of variants that are nonref in this individual
        # by index in self.variants
        self._which_variants_are_relevant = defaultdict(list)
        for i, variant in enumerate(self.variants):
            for indiv_id, genotype in get_quality_filtered_genotypes(variant, self.quality_filter):
                self.indiv_genotypes[indiv_id].append(genotype)
                self._which_variants_are_relevant[indiv_id].append(i)

    def get_individual_genotypes(self, indiv_id):
        return self.indiv_genotypes[indiv_id]

    def get_gene_bounds(self):
        return self.reference.get_gene_bounds(self.gene_id)

    def num_variants(self):
        return len(self.variants)

    def get_relevant_variants_for_indiv_ids(self, indiv_id_list):
        """
        Get a list of the variants that have at least one alt allele in any of these individuals
        """
        indices = [i for indiv_id in indiv_id_list for i in self._which_variants_are_relevant[indiv_id]]
        return [self.variants[i] for i in set(indices)]


def get_genes(datastore, reference, cohort, variant_filter=None, user=None):
    """
    Returns cohort variants grouped by gene
    TODO: quality filter. Need to set to null genotype instead of removing variant
    """
    variants = datastore.get_variants(cohort.project_id, cohort.cohort_id, variant_filter=variant_filter, user=user)
    for gene_id, variant_list in stream_utils.variant_stream_to_gene_stream(variants, reference):
        yield gene_id, variant_list


def get_homozygous_recessive_individuals(gene_variation, indiv_id_list):
    """
    An individual is homozygous recessive if htey have *any* homozygous alternate genotypes in this gene
    """
    ret = []
    for indiv_id in indiv_id_list:
        for genotype in gene_variation.get_individual_genotypes(indiv_id):
            if genotype.num_alt == 2:
                ret.append(indiv_id)
                break  # stop looking at this individual's genotypes; nothing else matters
    return ret


def get_x_linked_recessive_individuals(gene_variation, indiv_id_list):
    """
    An individual is X-linked recessive if they have a homozygous recessive variant *on the X chromosome*
    Right now this is equivalent to homozygous_recessive, but hopefully won't be when we get phased genotypes
    """
    # ignore if any variants in gene_variation are not on X chromosome
    # should not occur, as caller should know where gene_variation comes from, but hey, we check anyway
    if any(variant for variant in gene_variation.variants if variant.chr != 'chrX'):
        return []
    ret = []
    for indiv_id in indiv_id_list:
        for genotype in gene_variation.get_individual_genotypes(indiv_id):
            if genotype.num_alt == 2:
                ret.append(indiv_id)
                break  # stop looking at this individual's genotypes; nothing else matters
    return ret


def get_compound_het_individuals(gene_variation, indiv_id_list):
    """
    An individual is compound het if they have at least two heterozygous genotypes
    No other criteria are considered

    Returns list of indiv_ids
    """
    ret = []
    for indiv_id in indiv_id_list:
        het_genotypes = [g for g in gene_variation.get_individual_genotypes(indiv_id) if g.num_alt == 1]
        if len(het_genotypes) > 1:
            ret.append(indiv_id)

    return ret


def get_dominant_individuals(gene_variation, indiv_id_list):
    """
    For the indivs in indiv_id_list, which have dominant variation in this gene?
    That just means that they have at least one het variant - no other criteria are considered

    Returns list of indiv_ids
    """
    ret = []
    for indiv_id in indiv_id_list:
        for genotype in gene_variation.get_individual_genotypes(indiv_id):
            if genotype.num_alt == 1:
                ret.append(indiv_id)
                break  # stop looking at this individual's genotypes; nothing else matters
    return ret


def get_recessive_individuals(gene_variation, indiv_id_list):
    """
    An individual is recessive if they have *any* homozyogus recessvie, x-linked, or compound het recessive inheritance
    """
    list_of_lists = [
        get_homozygous_recessive_individuals(gene_variation, indiv_id_list),
        get_compound_het_individuals(gene_variation, indiv_id_list),
    ]
    if genomeloc.get_chr_pos(gene_variation.get_gene_bounds()[0])[0] == 'chrX':
        list_of_lists.append(get_x_linked_recessive_individuals(gene_variation, indiv_id_list))
    return set([indiv_id for indiv_list in list_of_lists for indiv_id in indiv_list])


INHERITANCE_VECTOR_FUNCTIONS = {
    'recessive': get_recessive_individuals,
    'homozygous_recessive': get_homozygous_recessive_individuals,
    'x_linked_recessive': get_x_linked_recessive_individuals,
    'compound_het': get_compound_het_individuals,
    'dominant': get_dominant_individuals,
}


def get_individuals_with_inheritance(inheritance_mode, gene_variation, indiv_id_list):
    """
    Figure out which individuals in indiv_id_list have a given inheritance within this set of variants
    Returns a dict of indiv_id -> True/False
    TODO: lots of optimization possible if necessary
    """
    return INHERITANCE_VECTOR_FUNCTIONS[inheritance_mode](gene_variation, indiv_id_list)


def get_genes_with_inheritance(datastore, reference, cohort, inheritance_mode, variant_filter=None, quality_filter=None, user=None):
    """
    """
    for gene_id, raw_variant_list in get_genes(datastore, reference, cohort, variant_filter, user=user):
        variant_list = search_utils.filter_gene_variants_by_variant_filter(raw_variant_list, gene_id, variant_filter)
        gene_variation = CohortGeneVariation(reference, gene_id, variant_list, cohort.indiv_id_list(), quality_filter=quality_filter)
        indivs_with_inheritance = get_individuals_with_inheritance(inheritance_mode, gene_variation, cohort.indiv_id_list())
        if len(indivs_with_inheritance) > 0:
            yield gene_id, indivs_with_inheritance, gene_variation


def get_individuals_with_inheritance_in_gene(datastore, reference, cohort, inheritance_mode, gene_id, variant_filter=None, quality_filter=None):
    variant_list = list(datastore.get_variants_in_gene(
        cohort.project_id,
        cohort.cohort_id,
        gene_id,
        variant_filter=variant_filter,
    ))
    variant_list = search_utils.filter_gene_variants_by_variant_filter(variant_list, gene_id, variant_filter)
    gene_variation = CohortGeneVariation(reference, gene_id, variant_list, cohort.indiv_id_list(), quality_filter=quality_filter)
    indivs_with_inheritance = get_individuals_with_inheritance(inheritance_mode, gene_variation, cohort.indiv_id_list())
    return indivs_with_inheritance, gene_variation


