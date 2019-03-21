from reference_data.models import GeneInfo


def get_genes_by_symbol():
    gene_symbol_to_genes = {}
    for gene_info in GeneInfo.objects.all().only('gene_id', 'gene_symbol').order_by('-gencode_release'):
        if gene_info.gene_symbol not in gene_symbol_to_genes:
            gene_symbol_to_genes[gene_info.gene_symbol] = gene_info
    return gene_symbol_to_genes
