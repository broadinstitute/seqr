from django.db.models import Count

from reference_data.models import GeneInfo
from seqr.views.utils.orm_to_json_utils import get_json_for_genes, get_json_for_gene


def get_gene(gene_id, user):
    gene = GeneInfo.objects.get(gene_id=gene_id)
    gene_json = get_json_for_gene(
        gene, user=user, add_dbnsfp=True, add_omim=True, add_constraints=True, add_notes=True, add_expression=True
    )
    return gene_json


def get_genes(gene_ids, **kwargs):
    genes = GeneInfo.objects.filter(gene_id__in=gene_ids)
    return {gene['geneId']: gene for gene in get_json_for_genes(genes, **kwargs)}


def get_gene_symbols_to_gene_ids(gene_symbols):
    genes = GeneInfo.objects.filter(gene_symbol__in=gene_symbols).only('gene_symbol', 'gene_id')
    return {gene.gene_symbol: gene.gene_id for gene in genes}


def get_gene_ids_to_gene_symbols(gene_ids=None):
    filter = {}
    if gene_ids:
        filter['gene_id__in'] = gene_ids
    genes = GeneInfo.objects.filter(**filter).only('gene_symbol', 'gene_id')
    return {gene.gene_id: gene.gene_symbol for gene in genes}


def get_filtered_gene_ids(gene_filter):
    return [gene.gene_id for gene in GeneInfo.objects.only('gene_id').filter(**gene_filter)]


def get_gene_bounds(gene_id):
    gene = GeneInfo.objects.filter(gene_id=gene_id).only('chrom_grch37', 'start_grch37', 'end_grch37').first()
    return (gene.chrom_grch37, gene.start_grch37, gene.end_grch37) if gene else (None, None, None)


def get_genes_omim_counts(gene_ids):
    genes = GeneInfo.objects.filter(gene_id__in=gene_ids).annotate(omim_count=Count('omim_set')).only('omim_count', 'gene_id')
    return {gene.gene_id: gene.omim_count for gene in genes}


def get_gene_id_from_str(s):
    """
    Given an arbitrary string s, see if you can use reference
    to get a gene ID (ensembl ID)
    """
    if GeneInfo.objects.filter(gene_id=s).count():
        return s
    gene = GeneInfo.objects.filter(gene_symbol=s).only('gene_id')
    if gene:
        return gene.gene_id
    return None
