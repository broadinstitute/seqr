from xbrowse.utils import region_utils
from .classes import CodingRegion


def get_coding_regions_from_gene_structure(gene_id, gene_structure):
    """
    Get list of sorted coding regions for gene
    (assuming gene['cds'] contains raw cds vals
    """
    cdr_list = []
    cdrs = [(c['cds_xstart'], c['cds_xstop']) for c in gene_structure['exons'] if 'cds_xstart' in c]
    cdrs = sorted(cdrs, key=lambda x: (x[0], x[1]))
    flattened_cdrs = region_utils.flatten_region_list(cdrs)
    for i, cdr_t in enumerate(flattened_cdrs):
        cdr_list.append(CodingRegion(gene_id=gene_id, index_in_gene=i, xstart=cdr_t[0], xstop=cdr_t[1]))
    return cdr_list



def get_coding_size_from_gene_structure(gene_id, gene_structure):
    """
    Get the total coding size - the sum of all coding regions
    """
    regions = get_coding_regions_from_gene_structure(gene_id, gene_structure)
    coding_size = 0
    for r in regions:
        coding_size += r.xstop - r.xstart + 1
    return coding_size