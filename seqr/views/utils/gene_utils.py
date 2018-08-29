from reference_data.models import GeneInfo
from seqr.views.utils.orm_to_json_utils import get_json_for_genes, get_json_for_gene
from xbrowse_server.mall import get_reference


def get_gene(gene_id, user):
    gene = GeneInfo.objects.get(gene_id=gene_id)
    gene_json = get_json_for_gene(gene, user=user, add_notes=True)
    # TODO load expression data into postgres reference_data
    gene_json['expression'] = get_reference().get_tissue_expression_display_values(gene_id)
    return gene_json


def get_genes(gene_ids):
    genes = GeneInfo.objects.filter(gene_id__in=gene_ids)
    return {gene['geneId']: gene for gene in get_json_for_genes(genes)}


def get_gene_symbols_to_gene_ids(gene_symbols):
    genes = GeneInfo.objects.filter(gene_symbol__in=gene_symbols)
    return {gene.symbol: gene.gene_id for gene in genes}
