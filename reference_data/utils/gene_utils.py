from reference_data.models import GeneInfo


def get_genes_by_id_and_symbol():
    gene_symbol_to_genes = {}
    gene_id_to_genes = {}
    for gene_info in GeneInfo.objects.all().only('gene_id', 'gene_symbol').order_by('-gencode_release'):
        if gene_info.gene_symbol not in gene_symbol_to_genes:
            gene_symbol_to_genes[gene_info.gene_symbol] = gene_info
        if gene_info.gene_id not in gene_id_to_genes:
            gene_id_to_genes[gene_info.gene_id] = gene_info
    return gene_id_to_genes, gene_symbol_to_genes
