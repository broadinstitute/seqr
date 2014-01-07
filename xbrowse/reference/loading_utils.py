

def get_coding_size_from_gene_structure(gene):
    """
    Get the total coding size - the sum of all coding regions
    """
    coding_size = 0
    for cds in gene['cds']:
        coding_size += cds['xstop'] - cds['xstart'] + 1
    return coding_size