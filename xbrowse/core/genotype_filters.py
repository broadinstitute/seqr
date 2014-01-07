GENOTYPE_FILTER_KEYS = ['vcf_filter', 'min_gq', 'min_ab']


def passes_genotype_filter(genotype, genotype_filter):
    """
    Does this genotype pass genotype_filter?
    """

    # VCF filter
    if 'vcf_filter' in genotype_filter:
        if genotype.filter != genotype_filter['vcf_filter']:
            return False

    # GQ
    if 'min_gq' in genotype_filter and genotype_filter['min_gq'] > 0:
        if genotype.gq is None or genotype.gq < genotype_filter['min_gq']:
            return False

    # AB - only applies if genotype is het
    if 'min_ab' in genotype_filter and genotype_filter['min_ab'] > 0:
        if genotype.num_alt == 1:
            if genotype.ab is None or genotype.ab*100 < genotype_filter['min_ab']:
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