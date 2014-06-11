from xbrowse import utils

def get_disease_gene_mapping(reference, lists):
    """
    Return a map of gene_id -> disease gene slugs
    for all the gene lists in lists/
    Called at startup by settings
    """
    ret = {gene_t[0]: [] for gene_t in reference.get_ordered_genes()}

    for item in lists:
        for line in open(item['filename']):
            gene_str = line.strip('\n')
            gene_id = utils.get_gene_id_from_str(gene_str, reference)
            ret[gene_id].append(item['slug'])
    return ret