from xbrowse import vcf_stuff

def error_in_before_load_qc(qc_results): 
    """
    Boolean, whether there was an error in given qc_results object
    """
    if qc_results['valid_vcf'] == False: return True
    if qc_results['has_indivs_missing_from_vcf'] == True: return True

    return False

def family_before_load_qc(family):
    """
    QC stuff before variant data is loaded
    Should be called before assign_variant_files
    Returns tuple of (has_error, qc_results), where qc_obj is: 
    {
        'valid_vcf': ...
        'has_indivs_missing_from_vcf': ...
        'indivs_missing_from_vcf': ...
    }
    """

    # TODO
    qc_results = {}
    qc_results['valid_vcf'] = True
    qc_results['has_indivs_missing_from_vcf'] = False

    return error_in_before_load_qc(qc_results), qc_results

def project_qc(db, project_id): 
    """
    QC for a project
    Returns ( [True/False, whether there was an error], [QC object] )
    """
    pass

def family_qc(db, family): 
    """
    Family QC 
    """
    pass

def extra_indivs_in_vcf(family_set, vcf_file): 
    """
    Get indiv_ids in the VCF file that are not accounted for by the individuals in family_set
    Can be extra indivs in families
    """
    ids_in_vcf = vcf_stuff.get_ids_from_vcf_path(vcf_file)
    seen = {indiv_id: False for indiv_id in ids_in_vcf}
    for family in family_set: 
        for indiv_id in family['individuals']: 
            if indiv_id in seen: 
                seen[indiv_id] = True

    return [i for i in seen if seen[i] == False]

def missing_from_vcf(family_set, vcf_file): 
    """
    Get indiv_ids in the VCF file that are not accounted for by the individuals in family_set
    Can be extra indivs in families
    """
    not_seen = set()
    for family in family_set: 
        for indiv_id in family['individuals']: 
            not_seen.add(indiv_id)
    for indiv_id in set(vcf_stuff.get_ids_from_vcf_path(vcf_file)):
        not_seen.discard(indiv_id)
    return list(not_seen)


