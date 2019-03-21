import re
from collections import defaultdict
from django.db.models import Q
from django.db.models.functions import Length

from reference_data.models import GeneInfo
from seqr.utils.xpos_utils import get_xpos
from seqr.views.utils.orm_to_json_utils import get_json_for_genes, get_json_for_gene


def get_gene(gene_id, user):
    gene = GeneInfo.objects.get(gene_id=gene_id)
    gene_json = get_json_for_gene(
        gene, user=user, add_dbnsfp=True, add_omim=True, add_constraints=True, add_notes=True, add_expression=True, add_mgi=True
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


def parse_locus_list_items(request_json):
    raw_items = request_json.get('rawItems')
    if not raw_items:
        return None, None, None

    invalid_items = []
    intervals = []
    gene_ids = set()
    gene_symbols = set()
    for item in raw_items.replace(',', ' ').split():
        interval_match = re.match('(?P<chrom>\w+):(?P<start>\d+)-(?P<end>\d+)', item)
        if interval_match:
            interval = interval_match.groupdict()
            try:
                interval['chrom'] = interval['chrom'].lstrip('chr')
                interval['start'] = int(interval['start'])
                interval['end'] = int(interval['end'])
                if interval['start'] > interval['end']:
                    raise ValueError
                get_xpos(interval['chrom'], interval['start'])
                intervals.append(interval)
            except (KeyError, ValueError):
                invalid_items.append('chr{chrom}:{start}-{end}'.format(
                    chrom=interval.get('chrom'), start=interval.get('start'), end=interval.get('end')
                ))
        elif item.upper().startswith('ENSG'):
            gene_ids.add(item)
        else:
            gene_symbols.add(item)

    gene_symbols_to_ids = get_gene_ids_for_gene_symbols(gene_symbols)
    invalid_items += [symbol for symbol in gene_symbols if not gene_symbols_to_ids.get(symbol)]
    gene_ids.update({gene_ids[0] for gene_ids in gene_symbols_to_ids.values() if len(gene_ids)})
    genes_by_id = get_genes(list(gene_ids), add_dbnsfp=True, add_omim=True, add_constraints=True) if gene_ids else {}
    invalid_items += [gene_id for gene_id in gene_ids if not genes_by_id.get(gene_id)]
    return genes_by_id, intervals, invalid_items