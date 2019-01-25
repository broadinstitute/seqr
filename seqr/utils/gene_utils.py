from collections import defaultdict
from django.db.models import Q
from django.db.models.functions import Length

from reference_data.models import GeneInfo
from seqr.utils.xpos_utils import get_xpos
from seqr.views.utils.orm_to_json_utils import get_json_for_genes, get_json_for_gene


def get_gene(gene_id, user):
    gene = GeneInfo.objects.get(gene_id=gene_id)
    gene_json = get_json_for_gene(
        gene, user=user, add_dbnsfp=True, add_omim=True, add_constraints=True, add_notes=True, add_expression=True
    )
    return gene_json


def get_genes(gene_ids, **kwargs):
    gene_filter = {}
    if gene_ids is not None:
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


def parse_locus_list_items(request_json, all_new=False):
    requested_items = (request_json.get('parsedItems') or {}).get('items') or []

    existing_gene_ids = set()
    new_gene_symbols = set()
    new_gene_ids = set()
    existing_interval_guids = set()
    new_intervals = []
    invalid_items = []
    for item in requested_items:
        if item.get('locusListIntervalGuid') and not all_new:
            existing_interval_guids.add(item.get('locusListIntervalGuid'))
        elif item.get('geneId'):
            if item.get('symbol') and not all_new:
                existing_gene_ids.add(item.get('geneId'))
            else:
                new_gene_ids.add(item.get('geneId'))
        elif item.get('symbol'):
            new_gene_symbols.add(item.get('symbol'))
        else:
            try:
                item['start'] = int(item['start'])
                item['end'] = int(item['end'])
                if item['start'] > item['end']:
                    raise ValueError
                get_xpos(item['chrom'], int(item['start']))
                new_intervals.append(item)
            except (KeyError, ValueError):
                invalid_items.append('chr{chrom}:{start}-{end}'.format(
                    chrom=item.get('chrom', '?'), start=item.get('start', '?'), end=item.get('end', '?')
                ))

    gene_symbols_to_ids = get_gene_ids_for_gene_symbols(new_gene_symbols)
    invalid_items += [symbol for symbol in new_gene_symbols if not gene_symbols_to_ids.get(symbol)]
    invalid_items += [symbol for symbol in new_gene_symbols if len(gene_symbols_to_ids.get(symbol, [])) > 1]
    new_genes = get_genes([gene_ids[0] for gene_ids in gene_symbols_to_ids.values() if len(gene_ids) == 1] + list(new_gene_ids),
                          add_dbnsfp=True, add_omim=True, add_constraints=True)
    invalid_items += [gene_id for gene_id, gene in new_genes.items() if not gene]
    new_genes = {gene_id: gene for gene_id, gene in new_genes.items() if gene}

    if all_new:
        return new_genes, new_intervals, invalid_items
    else:
        return new_genes, existing_gene_ids, new_intervals, existing_interval_guids, invalid_items
