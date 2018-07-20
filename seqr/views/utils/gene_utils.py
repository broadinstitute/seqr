from seqr.views.utils.json_utils import _to_camel_case
from xbrowse_server.mall import get_reference

# TODO create new reference data handler for seqr


def get_gene(gene_id):
    reference = get_reference()
    gene = reference.get_gene(gene_id)
    gene['expression'] = reference.get_tissue_expression_display_values(gene_id)
    return _gene_json(gene)


def get_genes(gene_ids):
    reference = get_reference()
    genes = reference.get_genes(gene_ids)
    return {geneId: _gene_json(gene) for geneId, gene in genes.items()}


def get_gene_symbols_to_gene_ids(gene_symbols):
    reference = get_reference()
    return {symbol: reference.get_gene_id_from_symbol(symbol) for symbol in gene_symbols}


def _parse_gene_constraints(gene):
    gene_tags = gene.get('tags', gene)
    return {
       'lof': {
           'constraint': gene_tags.get('lof_constraint'),
           'rank': gene_tags.get('lof_constraint_rank') and gene_tags['lof_constraint_rank'][0],
           'totalGenes': gene_tags.get('lof_constraint_rank') and gene_tags['lof_constraint_rank'][1],
       },
       'missense': {
           'constraint': gene_tags.get('missense_constraint'),
           'rank': gene_tags.get('missense_constraint_rank') and gene_tags['missense_constraint_rank'][0],
           'totalGenes': gene_tags.get('missense_constraint_rank') and gene_tags['missense_constraint_rank'][1],
       },
   }


def _gene_json(gene):
    gene['constraints'] = _parse_gene_constraints(gene)
    gene = {_to_camel_case(k): v for k, v in gene.items()}
    gene['phenotypeInfo'] = {_to_camel_case(k): v for k, v in gene.get('phenotypeInfo', {}).items()}
    return gene
