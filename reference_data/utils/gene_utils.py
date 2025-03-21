from reference_data.models import GeneInfo


def get_genes_by_id_and_symbol():
    gene_symbol_to_genes = {}
    gene_id_to_genes = {}
    for db_id, gene_id, gene_symbol in GeneInfo.objects.all().order_by('-gencode_release').values_list('id', 'gene_id', 'gene_symbol'):
        if gene_symbol not in gene_symbol_to_genes:
            gene_symbol_to_genes[gene_symbol] = gene_id
        if gene_id not in gene_id_to_genes:
            gene_id_to_genes[gene_id] = db_id
    return gene_id_to_genes, gene_symbol_to_genes
