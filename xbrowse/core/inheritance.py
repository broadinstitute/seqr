# TODO: where should we keep this file?

def get_homozygous_recessive_filter(family):
    """
    Returns a genotype filter for homozygous recessive variants for family: 
    -- Affecteds must be homozygous alt
    -- Parents of affected are heterozygous (unless they are affected, in which case hom alt)
    -- Unaffecteds have at least one ref allele
    """
    genotype_filter = {}

    # set affected and unaffected genotypes first, without inheritance
    for indiv_id, individual in family.individuals.items():

        if individual.affected_status == 'affected':
            genotype_filter[indiv_id] = 'alt_alt'
        elif individual.affected_status == 'unaffected':
            genotype_filter[indiv_id] = 'has_ref'

    # now account for parental relationships (but no others)
    for indiv_id, individual in family.individuals.items():
        father = family.get_individual(individual.paternal_id)
        mother = family.get_individual(individual.maternal_id)

        if individual.affected_status == 'affected':

            if mother is not None:
                # only set parents to has_ref if unaffected
                if mother.affected_status == 'unaffected':
                    genotype_filter[individual.maternal_id] = 'has_ref'

            if father is not None:
                # only set parents to has_ref if unaffected
                if father.affected_status == 'unaffected':
                    genotype_filter[individual.paternal_id] = 'has_ref'

    return genotype_filter

def get_de_novo_filter(family): 
    """
    Genotype filter for a single de novo variant
    -- Affecteds must be heterozygous
    -- Unaffecteds must be homozygous reference

    Note that this can catch (and has!) germline denovo variants in families with multiple affecteds

    """
    genotype_filter = {}

    # set affected and unaffected genotypes first, without inheritance
    for indiv_id, individual in family.individuals.items():

        if individual.affected_status == 'affected':
            genotype_filter[indiv_id] = 'has_alt'
        elif individual.affected_status == 'unaffected':
            genotype_filter[indiv_id] = 'ref_ref'

    return genotype_filter

def get_dominant_filter(family): 
    """
    """
    genotype_filter = {}

    # set affected and unaffected genotypes first, without inheritance
    for indiv_id, individual in family.individuals.items():

        if individual.affected_status == 'affected':
            genotype_filter[indiv_id] = 'has_alt'
        elif individual.affected_status == 'unaffected':
            genotype_filter[indiv_id] = 'ref_ref'

    return genotype_filter

def get_x_linked_filter(family): 
    """ 
    Genotype filter for x linked inheritnace
    This is the same as homozygous recessive, but male carriers are alt_alt, instead of ref_alt
    Note that this filter only looks at the genotypes, but ignores location
    Must combine with a variant filter that only looks at chrX
    """ 

    genotype_filter = {}

    # set affected and unaffected genotypes first, without inheritance
    for indiv_id, individual in family.individuals.items():

        if individual.affected_status == 'affected':
            genotype_filter[indiv_id] = 'alt_alt'
        elif individual.affected_status == 'unaffected':
            genotype_filter[indiv_id] = 'has_ref'           

    # now account for parental relationships (but no others)
    for indiv_id, individual in family.individuals.items():

        father = family.get_individual(individual.paternal_id)
        mother = family.get_individual(individual.maternal_id)

        if individual.affected_status == 'affected':

            if mother is not None:
                if mother.affected_status == 'unaffected':
                    genotype_filter[individual.maternal_id] = 'ref_alt'

            if father is not None:
                # if father is unaffected, should be ref_ref instead of ref_alt
                if father.affected_status == 'unaffected':
                    genotype_filter[individual.paternal_id] = 'ref_ref'

    return genotype_filter

def get_genotype_filters(family): 
    """
    Get a dict of slug -> genotype filter for a family
    """
    return {
        'homozygous_recessive': get_homozygous_recessive_filter(family), 
        'de_novo': get_de_novo_filter(family), 
        'x_linked_recessive': get_x_linked_filter(family),
        'dominant': get_dominant_filter(family),
    }


def dominant_makes_sense_for_family(family):
    if family.num_individuals() < 2:
        return False
    else:
        return not denovo_makes_sense_for_family(family)


def recessive_makes_sense_for_family(family):
    return family.num_individuals() > 1 and len(family.get_affecteds()) < family.num_individuals()


def denovo_makes_sense_for_family(family):
    """
    At least one affected has to have two unaffected parents
    """
    for indiv in family.get_affecteds():
        if family.contains_indiv_id(indiv.paternal_id) and family.contains_indiv_id(indiv.maternal_id):
            if family.get_individual(indiv.paternal_id).affected_status == 'unaffected' and family.get_individual(indiv.maternal_id).affected_status == 'unaffected':
                return True
    return False


MAKES_SENSE_FUNCTIONS = {
    'recessive': recessive_makes_sense_for_family,
    'homozygous_recessive': recessive_makes_sense_for_family,
    'x_linked_recessive': recessive_makes_sense_for_family,  # TODO: should this be separate?
    'compound_het': recessive_makes_sense_for_family,
    'dominant': dominant_makes_sense_for_family,
    'de_novo': denovo_makes_sense_for_family,
}


def inheritance_makes_sense_for_family(family, inheritance_mode):
    """
    Does it make sense to search for inheritance_mode for family?
    """
    return MAKES_SENSE_FUNCTIONS[inheritance_mode](family)








