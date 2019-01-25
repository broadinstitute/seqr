from collections import defaultdict
from django.db.models import Q
from django.db.models.functions import Length

from reference_data.models import GeneInfo
from seqr.views.utils.orm_to_json_utils import get_json_for_genes, get_json_for_gene


def get_gene(gene_id, user):
    gene = GeneInfo.objects.get(gene_id=gene_id)
    gene_json = get_json_for_gene(
        gene, user=user, add_dbnsfp=True, add_omim=True, add_constraints=True, add_notes=True, add_expression=True
    )
    return gene_json


def get_genes(gene_ids, **kwargs):
    gene_filter = {}
    if gene_ids:
        gene_filter['gene_id__in'] = gene_ids
    genes = GeneInfo.objects.filter(**gene_filter)
    return {gene['geneId']: gene for gene in get_json_for_genes(genes, **kwargs)}


def get_gene_ids_for_gene_symbols(gene_symbols):
    genes = GeneInfo.objects.filter(gene_symbol__in=gene_symbols).only('gene_symbol', 'gene_id').order_by('-gencode_release')
    symbols_to_ids = defaultdict(list)
    for gene in genes:
        symbols_to_ids[gene.gene_symbol].append(gene.gene_id)
    return symbols_to_ids


def get_filtered_gene_ids(gene_filter):
    return [gene.gene_id for gene in GeneInfo.objects.only('gene_id').filter(**gene_filter)]


def get_queried_genes(query, max_results):
    matching_genes = GeneInfo.objects.filter(
        Q(gene_id__icontains=query) | Q(gene_symbol__icontains=query)
    ).only('gene_id', 'gene_symbol').order_by(Length('gene_symbol').asc()).distinct()
    return [{'gene_id': gene.gene_id, 'gene_symbol': gene.gene_symbol} for gene in matching_genes[:max_results]]
