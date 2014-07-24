
def get_variant_display_headers(indiv_id_list=None):
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
        'g1k_aaf',
        'esp_ea_aaf',
        'esp_aa_aaf',
        'atgu_controls_aaf',
    ]

    if indiv_id_list:
        for indiv_id in indiv_id_list:
            headers.append(indiv_id)
            headers.append(indiv_id+'_gq')
            headers.append(indiv_id+'_dp')

    return headers


def get_display_fields_for_variant(variant, reference, indiv_id_list=None):
    """
    Return a list of strings that can be output as a tsv or spreadsheet
    """
    fields = []
    genes = [reference.get_gene_symbol(gene_id) for gene_id in variant.coding_gene_ids]
    fields.append(','.join(genes))
    fields.extend([
        variant.chr,
        str(variant.pos),
        variant.ref,
        variant.alt,
        variant.annotation.get('vep_group', '.'),
        str(variant.annotation['freqs']['g1k_all']),
        str(variant.annotation['freqs']['esp_ea']),
        str(variant.annotation['freqs']['esp_aa']),
        str(variant.annotation['freqs']['atgu_controls']),
    ])
    if indiv_id_list is None:
        indiv_id_list = []
    for indiv_id in indiv_id_list:
        genotype = variant.get_genotype(indiv_id)
        if not genotype:
            fields.extend(['.', '.', '.'])
        else:
            fields.append(str(genotype.num_alt) if genotype.num_alt is not None else '.')
            fields.append(str(genotype.gq) if genotype.gq is not None else '.')
            fields.append(genotype.extras['dp'] if genotype.extras.get('dp') is not None else '.')
    return fields