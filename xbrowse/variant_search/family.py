"""
Contains vairant search methods for family variants
"""

import itertools
import sys
from collections import defaultdict
from xbrowse import inheritance
from xbrowse import genomeloc
from xbrowse import stream_utils
from xbrowse import inheritance_modes
from xbrowse import utils
from xbrowse import Variant
from xbrowse.variant_search import utils as search_utils
from xbrowse.core.genotype_filters import passes_genotype_filter, filter_genotypes_for_quality
from xbrowse.core.variant_filters import passes_allele_count_filter, passes_variant_filter

def passes_quality_filter(variant, quality_filter, indivs_to_consider):
    """
    Does variant pass given the items in quality_filter?
    Return True or False
    TODO: this is weird
    """
    for indiv_id in indivs_to_consider:
        genotype = variant.get_genotype(indiv_id)
        if not passes_genotype_filter(genotype, quality_filter):
            return False

    return True


def get_variants(
        datastore,
        family,
        genotype_filter=None,
        variant_filter=None,
        quality_filter=None,
        indivs_to_consider=None):
    """
    Gets family variants that pass the optional filters
    Can be called directly, but most often proxied by direct methods below
    """
    counters = defaultdict(int)
    for variant in datastore.get_variants(
            family.project_id,
            family.family_id,
            genotype_filter=genotype_filter,
            variant_filter=variant_filter
    ):

        # # first check if we should filter out from the custom populations filter
        # if custom_populations_filter:
        #     if not mall.custom_population_store.passes_frequency_filters(
        #         variant.xpos,
        #         variant.ref,
        #         variant.alt,
        #         custom_populations_filter
        #     ):
        #         continue

        if quality_filter is None:
            yield variant
        else:
            if indivs_to_consider is None:
                if genotype_filter:
                    indivs_to_consider = genotype_filter.keys()
                else:
                    indivs_to_consider = []

            if passes_quality_filter(variant, quality_filter, indivs_to_consider):
                counters["passes_quality_filters"] += 1
                yield variant
    for k, v in counters.items():
        sys.stderr.write("    %s: %s\n" % (k, v))


def get_homozygous_recessive_variants(datastore, reference, family, variant_filter=None, quality_filter=None):
    """
    Returns variants that follow homozygous recessive inheritance in family
    """
    genotype_filter = inheritance.get_homozygous_recessive_filter(family)
    for variant in get_variants(
        datastore,
        family,
        genotype_filter=genotype_filter,
        variant_filter=variant_filter,
        quality_filter=quality_filter,
        indivs_to_consider=family.indiv_id_list(),
    ):
        yield variant


def get_de_novo_variants(datastore, reference, family, variant_filter=None, quality_filter=None):
    """
    Returns variants that follow homozygous recessive inheritance in family
    """
    de_novo_filter = inheritance.get_de_novo_filter(family)
    db_query = datastore._make_db_query(de_novo_filter, variant_filter)

    collection = datastore._get_family_collection(family.project_id, family.family_id)
    if not collection:
        raise ValueError("Error: mongodb collection not found for project %s family %s " % (family.project_id, family.family_id))

    MONGO_QUERY_RESULTS_LIMIT = 5000
    variant_iter = collection.find(db_query).sort('xpos').limit(MONGO_QUERY_RESULTS_LIMIT+5)

    # get ids of parents in this family
    valid_ids = set(indiv_id for indiv_id in family.individuals)
    paternal_ids = set(i.paternal_id for i in family.get_individuals() if i.paternal_id in valid_ids)
    maternal_ids = set(i.maternal_id for i in family.get_individuals() if i.maternal_id in valid_ids)
    parental_ids = paternal_ids | maternal_ids

    # loop over all variants returned
    for i, variant_dict in enumerate(variant_iter):
        if i > MONGO_QUERY_RESULTS_LIMIT:
            raise Exception("MONGO_QUERY_RESULTS_LIMIT of %s exceeded for query: %s" % (MONGO_QUERY_RESULTS_LIMIT, db_query))

        variant = Variant.fromJSON(variant_dict)
        datastore.add_annotations_to_variant(variant, family.project_id)
        if not passes_variant_filter(variant, variant_filter)[0]:
            continue

        # handle genotype filters
        if len(parental_ids) != 2:
            # ordinary filters for non-trios
            for indiv_id in de_novo_filter.keys():
                genotype = variant.get_genotype(indiv_id)
                if not passes_genotype_filter(genotype, quality_filter):
                    break
            else:
                yield variant
        else:
            # for trios use Mark's recommended filters for de-novo variants:
            # Hard-coded thresholds:
            #   1) Child must have > 10% of combined Parental Read Depth
            #   2) MinimumChildGQscore >= 20
            #   3) MaximumParentAlleleBalance <= 5%
            # Adjustable filters:
            #   Variants should PASS
            #   Child AB should be >= 20

            # compute parental read depth for filter 1
            total_parental_read_depth = 0
            for indiv_id in parental_ids:
                genotype = variant.get_genotype(indiv_id)
                if genotype.extras and 'dp' in genotype.extras:
                    total_parental_read_depth += int(genotype.extras['dp'])
                else:
                    total_parental_read_depth = None  # both parents must have DP to use the parental_read_depth filters 
                    break
                
            for indiv_id in de_novo_filter.keys():            
                quality_filter_temp = quality_filter.copy()  # copy before modifying
                if indiv_id in parental_ids:
                    # handle one of the parents
                    quality_filter_temp['max_ab'] = 5
                else: 
                    # handle child
                    quality_filter_temp['min_gq'] = 20
                    if total_parental_read_depth is not None:
                        quality_filter_temp['min_dp'] = total_parental_read_depth * 0.1

                genotype = variant.get_genotype(indiv_id)
                if not passes_genotype_filter(genotype, quality_filter_temp):
                    #print("%s: %s " % (variant.chr, variant.pos))
                    break
            else:
                yield variant


def get_dominant_variants(datastore, reference, family, variant_filter=None, quality_filter=None):
    """
    Returns variants that follow dominant inheritance in family
    """
    dominant_filter = inheritance.get_dominant_filter(family)
    for variant in get_variants(datastore, family, genotype_filter=dominant_filter, variant_filter=variant_filter, quality_filter=quality_filter, indivs_to_consider=family.indiv_id_list()):
        yield variant


def get_x_linked_variants(datastore, reference, family, variant_filter=None, quality_filter=None):
    """
    Variants that follow x linked inheritance in a family
    """
    x_linked_filter = inheritance.get_x_linked_filter(family)
    for variant in get_variants(datastore, family, genotype_filter=x_linked_filter, variant_filter=variant_filter, quality_filter=quality_filter, indivs_to_consider=family.indiv_id_list()):
        if genomeloc.get_chr_pos(variant.xpos)[0] == 'chrX':
            yield variant


def is_family_compound_het_for_combo(combo, family):
    """
    Is family compound het for the two variants in combo. Criteria:
    - no unaffected individuals can be het for both variants
    - no unaffected individuals can be homozygous alt for any variant
    TODO: need to figure out corner cases w affected individuals
    """
    valid = True
    for indiv_id, individual in family.individuals.items():
        if individual.affected_status == 'unaffected':

            # not compound het if *any* affected is homozygous alt for *any* variant
            if combo[0].get_genotype(indiv_id).num_alt > 1 or combo[1].get_genotype(indiv_id).num_alt > 1:
                valid = False

            # not compound het if *any* affected is het for *all* variants
            if combo[0].get_genotype(indiv_id).num_alt > 0 and combo[1].get_genotype(indiv_id).num_alt > 0:
                valid = False

    return valid


def get_compound_het_genes(datastore, reference, family, variant_filter=None, quality_filter=None):
    """
    Gene-based inheritance; genes with variants that follow compound het inheritance in a family
    Note that compound het implies two variants, so we look at all variant pairs
    Return is a stream of tuples (gene_name, variant_list)
    """

    # only ask for variants that are het in all affected
    initial_filter = {}
    for indiv_id, individual in family.individuals.items():
        if individual.affected_status == 'affected':
            initial_filter[indiv_id] = 'ref_alt'

    het_variants = get_variants(datastore, family, initial_filter, variant_filter, quality_filter, indivs_to_consider=family.indiv_id_list())
    for gene_name, raw_variants in stream_utils.variant_stream_to_gene_stream(het_variants, reference):

        variants = search_utils.filter_gene_variants_by_variant_filter(raw_variants, gene_name, variant_filter)

        variants_to_return = {}

        # don't care about genes w less than 2 variants
        if len(variants) < 2:
            continue

        combos = itertools.combinations(variants, 2)
        for combo in combos:
            valid = is_family_compound_het_for_combo(combo, family)
            if valid:
                variants_to_return[combo[0].unique_tuple()] = combo[0]
                variants_to_return[combo[1].unique_tuple()] = combo[1]

        if len(variants_to_return) > 0:
            yield (gene_name, variants_to_return.values())

def get_recessive_genes(datastore, reference, family, variant_filter=None, quality_filter=None):
    """
    Combination of homozygous recessive, x-linked, and compound het inheritances
    Gene-based, but genes are unique and variants within them unique too
    """
    #sys.stderr.write("     getting recessive genes for family: %s %s" % (family.project_id, family.family_id))

    # combine hom rec and x linked into single variant stream, then gene stream
    hom_rec_variants = get_homozygous_recessive_variants(datastore, reference, family, variant_filter, quality_filter)
    x_linked_variants = get_x_linked_variants(datastore, reference, family, variant_filter, quality_filter)
    single_variants = stream_utils.combine_variant_streams([hom_rec_variants, x_linked_variants])
    single_variants_by_gene = stream_utils.variant_stream_to_gene_stream(single_variants, reference)

    # combine with compound het genes
    compound_het_genes = get_compound_het_genes(datastore, reference, family, variant_filter, quality_filter)
    genes_with_duplicates = stream_utils.combine_gene_streams([single_variants_by_gene, compound_het_genes], reference)

    # return uniqified
    for item in stream_utils.remove_duplicate_variants_from_gene_stream(genes_with_duplicates):
        yield item

INHERITANCE_FUNCTIONS = {
    'recessive': get_recessive_genes,
    'homozygous_recessive': get_homozygous_recessive_variants,
    'x_linked_recessive': get_x_linked_variants,
    'compound_het': get_compound_het_genes,
    'dominant': get_dominant_variants,
    'de_novo': get_de_novo_variants,
}

def get_variants_with_inheritance_mode(mall, family, inheritance_mode, variant_filter=None, quality_filter=None):
    """
    Get variants in a family with inheritance_mode, using the functions in VARIANT_INHERITANCE_FUNCTIONS
    """

    if inheritance_modes.INHERITANCE_DEFAULTS_MAP[inheritance_mode]['datatype'] == 'variants':
        for variant in INHERITANCE_FUNCTIONS[inheritance_mode](mall.variant_store, mall.reference, family, variant_filter, quality_filter):
            yield variant
    else:
        for variant in stream_utils.gene_stream_to_variant_stream(INHERITANCE_FUNCTIONS[inheritance_mode](mall.variant_store, mall.reference, family, variant_filter, quality_filter), mall.reference):
            yield variant


def get_genes(db, reference, family, burden_filter=None, variant_filter=None, quality_filter=None):
    """
    Get gene stream for a family that meets the burden filter above
    Burden filters are analagous to genotype filters, but for gene burden:
    a dict of indiv_id -> key
    Currently available keys are: at_least_1, at_least_2, less_than_2, none
    All refer to allele counts
    Food for thought: should "compound_het" be a burden_filter in the future? Or does that go somewhere else?
    TODO: this is really slow right now, we need to optimize
    """
    indivs_to_consider = burden_filter.keys() if burden_filter else []
    variant_stream = get_variants(db, family, variant_filter=variant_filter, quality_filter=quality_filter)
    for gene_id, variant_list in stream_utils.variant_stream_to_gene_stream(variant_stream, reference):
        quality_filtered_variant_list = [v for v in variant_list if passes_quality_filter(v, quality_filter, indivs_to_consider)]
        if len(quality_filtered_variant_list) == 0:
            continue
        if burden_filter is None:
            yield gene_id, quality_filtered_variant_list
        elif _passes_burden_filter(quality_filtered_variant_list, burden_filter):
            yield gene_id, quality_filtered_variant_list


def _passes_burden_filter(variant_list, burden_filter):
    """
    Does the variant list here pass burden_filter?
    Returns True or False right now, may want to return list of relevant variants in the future
    """
    aac_map = utils.alt_allele_count_map(variant_list)
    for indiv_id, burden_key in burden_filter.items():
        if burden_key == 'at_least_1':
            if aac_map[indiv_id] < 1:
                return False
        elif burden_key == 'at_least_2':
            if aac_map[indiv_id] < 2:
                return False
        elif burden_key == 'less_than_2':
            if aac_map[indiv_id] > 1:
                return False
        elif burden_key == 'none':
            if aac_map[indiv_id] > 0:
                return False

    # if the burden filter didn't present anything to invalidate this variant list, it passed
    return True


def get_variants_allele_count(
        datastore,
        family,
        allele_count_filter,
        variant_filter=None,
        quality_filter=None):
    """
    This is a horrible hack to allow allele count-based searches in a family
    This needs to be refactored back into get_variants, but I'm not sure how to resolve the genotype quality stuff
    """
    for variant in datastore.get_variants(family.project_id, family.family_id, variant_filter=variant_filter):
        filter_genotypes_for_quality(variant, quality_filter)
        if passes_allele_count_filter(variant, allele_count_filter, family.affected_status_map()):
            yield variant
