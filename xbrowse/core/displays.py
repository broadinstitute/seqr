
def get_variant_display_headers(mall, project, indiv_id_list=None):
    """
    Get the list of header fields to display in a variants table
    Should match below
    TODO: should take annotation spec
    """
    headers = [
        'genes',
        'chr',
        'pos',
        'ref',
        'alt',
        'worst_annotation',
    ]
    headers.extend(project.get_reference_population_slugs())
    headers.extend([
        'polyphen',
        'sift',
        'muttaster',
        'fathmm',
    ])

    if indiv_id_list:
        for indiv_id in indiv_id_list:
            headers.append(indiv_id)
            headers.append(indiv_id+'_gq')
            headers.append(indiv_id+'_dp')

    return headers


def get_display_fields_for_variant(mall, project, variant, indiv_id_list=None):
    """
    Return a list of strings that can be output as a tsv or spreadsheet
    """
    fields = []
    genes = [mall.reference.get_gene_symbol(gene_id) for gene_id in variant.coding_gene_ids]
    fields.append(','.join(genes))
    fields.extend([
        variant.chr,
        str(variant.pos),
        variant.ref,
        variant.alt,
        variant.annotation.get('vep_group', '.'),
    ])
    for ref_population_slug in project.get_reference_population_slugs():
        fields.append(variant.annotation['freqs'][ref_population_slug])
    for field_key in ['polyphen', 'sift', 'muttaster', 'fathmm']:
        fields.append(variant.annotation.get(field_key, ''))
    if indiv_id_list is None:
        indiv_id_list = []
    for indiv_id in indiv_id_list:
        genotype = variant.get_genotype(indiv_id)
        if genotype is None:
            fields.extend(['.', '.', '.'])
        else:
            if genotype.num_alt == 0:
                fields.append("%s/%s" % (variant.ref, variant.ref))
            elif genotype.num_alt == 1:
                fields.append("%s/%s" % (variant.ref, variant.alt))
            elif genotype.num_alt == 2:
                fields.append("%s/%s" % (variant.alt, variant.alt))
            else:
                fields.append("./.")

            fields.append(str(genotype.gq) if genotype.gq is not None else '.')
            fields.append(genotype.extras['dp'] if genotype.extras.get('dp') is not None else '.')
    return fields