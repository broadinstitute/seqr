def get_parent_child_trios(family):
    """
    List of full (paternal_id, maternal_id, child_id) tuples in this family
    By full, we mean all three individuals exist in family
    """
    pass


def get_parent_child_pairs(family):
    """
    List of full (parent_id, child_id) tuples in this family
    """
    pass


def get_num_opposite_homozygotes(family, parent_child_pair, datastore):
    """
    Get the number of opposite-allele homozygotes for this parent and child
    Returns the integer count
    """
    # TODO: how to only consider biallelic snps
    pass


def get_proportion_shared_rare_variants(family, parent_child_pair, datastore):
    """
    Get the proportion (float) of rare heterozygous variants in child that are also present in parent
    So if child has 10 variants, and 4 come from this parent, returns 0.4
    """
    # TODO: how to only consider biallelic snps
    pass
