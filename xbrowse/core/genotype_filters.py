GENOTYPE_FILTER_KEYS = ['vcf_filter', 'min_gq', 'min_ab']


def passes_genotype_filter(genotype, genotype_filter):
    """
    Does this genotype pass genotype_filter?
    """
    if genotype is None:
        return False

    # VCF filter
    if 'vcf_filter' in genotype_filter:
        if genotype.filter != genotype_filter['vcf_filter']:
            return False

    # GQ
    if 'min_gq' in genotype_filter and genotype_filter['min_gq'] > 0:
        if genotype.gq is not None and genotype.gq < genotype_filter['min_gq']:
            #print("GQ: %s not > %s" % (genotype.gq, genotype_filter['min_gq'])) 
            return False

    # AB - only applies if genotype is het
    if 'min_ab' in genotype_filter and genotype_filter['min_ab'] > 0:
        if genotype.num_alt == 1:
            if genotype.ab is not None and genotype.ab*100 < genotype_filter['min_ab']:
                #print("AB: %s not < %s" % (genotype.ab and genotype.ab*100, genotype_filter['min_ab'])) 
                return False

    # AB - only applies if genotype is het
    if 'max_ab' in genotype_filter and genotype_filter['max_ab'] > 0:
        if genotype.num_alt == 1:
            if genotype.ab is not None and genotype.ab*100 > genotype_filter['max_ab']:
                #print("AB: %s not > %s" % (genotype.ab and genotype.ab*100, genotype_filter['max_ab'])) 
                return False

    # DP
    if 'min_dp' in genotype_filter and genotype_filter['min_dp'] > 0:
        if genotype.extras is not None and 'dp' in genotype.extras:
            dp = int(genotype.extras['dp'])
            if dp < genotype_filter['min_dp']:
                #print("DP: %s not < %s" % (dp, genotype_filter['min_dp'])) 
                return False

    return True


def filter_genotypes_for_quality(variant, genotype_filter):
    """
    Filter genotypes from variant that don't pass genotype_filter
    Filtered genotypes are just set to num_alt=None
    """
    for indiv_id, genotype in variant.get_genotypes():
        if not passes_genotype_filter(genotype, genotype_filter):
            variant.genotypes[indiv_id] = genotype._replace(num_alt=None)
