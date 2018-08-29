from reference_data.models import GeneInfo
from seqr.views.utils.orm_to_json_utils import get_json_for_genes, get_json_for_gene


def get_gene(gene_id):
    gene = GeneInfo.objects.get(gene_id=gene_id)
    return get_json_for_gene(gene, add_expression=True)


def get_genes(gene_ids):
    genes = GeneInfo.objects.filter(gene_id__in=gene_ids)
    return {gene['geneId']: gene for gene in get_json_for_genes(genes)}


def get_gene_symbols_to_gene_ids(gene_symbols):
    genes = GeneInfo.objects.filter(gene_symbol__in=gene_symbols)
    return {gene.symbol: gene.gene_id for gene in genes}
