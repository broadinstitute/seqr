from xbrowse.utils import region_utils
from .classes import CodingRegion


def get_coding_regions_for_gene(gene):
    """
    Get list of sorted coding regions for gene
    (assuming gene['cds'] contains raw cds vals
    """
    cdr_list = []
    # map of coordinate tuple -> cdr
    cdrs = [(c['xstart'], c['xstop']) for c in gene['cds']]
    flattened_cdrs = region_utils.flatten_region_list(cdrs)
    for i, cdr_t in enumerate(flattened_cdrs):
        cdr_list.append(CodingRegion(gene_id=gene['gene_id'], index_in_gene=i, xstart=cdr_t[0], xstop=cdr_t[1]))
    return cdr_list

