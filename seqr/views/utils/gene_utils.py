from seqr.utils.xpos_utils import get_xpos
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
    return {geneId: _gene_json(gene) if gene else None for geneId, gene in genes.items()}


def get_gene_symbols_to_gene_ids(gene_symbols):
    reference = get_reference()
    return {symbol: reference.get_gene_id_from_symbol(symbol) for symbol in gene_symbols}


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
                get_xpos(item['chrom'], item['start'])
                new_intervals.append(item)
            except (KeyError, ValueError):
                invalid_items.append('chr{chrom}:{start}-{end}'.format(
                    chrom=item.get('chrom', '?'), start=item.get('start', '?'), end=item.get('end', '?')
                ))

    gene_symbols_to_ids = get_gene_symbols_to_gene_ids(new_gene_symbols)
    invalid_items += [symbol for symbol, gene_id in gene_symbols_to_ids.items() if not gene_id]
    new_genes = get_genes([gene_id for gene_id in gene_symbols_to_ids.values() if gene_id] + list(new_gene_ids))
    invalid_items += [gene_id for gene_id, gene in new_genes.items() if not gene]
    new_genes = {gene_id: gene for gene_id, gene in new_genes.items() if gene}

    if all_new:
        return new_genes, new_intervals, invalid_items
    else:
        return new_genes, existing_gene_ids, new_intervals, existing_interval_guids, invalid_items


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
