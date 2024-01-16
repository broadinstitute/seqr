import re
from collections import defaultdict
from django.db.models import Q, prefetch_related_objects, Prefetch
from django.db.models.functions import Length

from reference_data.models import GeneInfo, GeneConstraint, dbNSFPGene, Omim, MGI, PrimateAI, GeneCopyNumberSensitivity, \
    GenCC, ClinGen, GeneShet
from seqr.utils.xpos_utils import get_xpos
from seqr.views.utils.orm_to_json_utils import _get_json_for_model, _get_json_for_models, _get_empty_json_for_model, \
    get_json_for_gene_notes_by_gene_id


def get_gene(gene_id, user):
    gene = GeneInfo.objects.get(gene_id=gene_id)
    gene_json = _get_json_for_model(gene, get_json_for_models=_get_json_for_genes, user=user, gene_fields=ALL_GENE_FIELDS)
    return gene_json


def get_genes(gene_ids):
    return _get_genes(gene_ids)


def get_genes_for_variant_display(gene_ids):
    return _get_genes(gene_ids, gene_fields=VARIANT_GENE_DISPLAY_FIELDS)


def get_genes_for_variants(gene_ids):
    return _get_genes(gene_ids, gene_fields=VARIANT_GENE_FIELDS)


def get_genes_with_detail(gene_ids, user):
    return _get_genes(gene_ids, user=user, gene_fields=ALL_GENE_FIELDS)


def _get_genes(gene_ids, user=None, gene_fields=None):
    gene_filter = {}
    if gene_ids is not None:
        gene_filter['gene_id__in'] = gene_ids
    genes = GeneInfo.objects.filter(**gene_filter)
    return {gene['geneId']: gene for gene in _get_json_for_genes(genes, user=user, gene_fields=gene_fields)}


def get_gene_ids_for_gene_symbols(gene_symbols):
    genes = GeneInfo.objects.filter(gene_symbol__in=gene_symbols).only('gene_symbol', 'gene_id').order_by('-gencode_release')
    symbols_to_ids = defaultdict(list)
    for gene in genes:
        symbols_to_ids[gene.gene_symbol].append(gene.gene_id)
    return symbols_to_ids


def get_filtered_gene_ids(gene_filter):
    return [gene.gene_id for gene in GeneInfo.objects.filter(gene_filter).only('gene_id')]


def get_queried_genes(query, max_results):
    matching_genes = GeneInfo.objects.filter(
        Q(gene_id__icontains=query) | Q(gene_symbol__icontains=query)
    ).only('gene_id', 'gene_symbol').order_by(Length('gene_symbol').asc(), 'gene_symbol').distinct()
    return [{'gene_id': gene.gene_id, 'gene_symbol': gene.gene_symbol} for gene in matching_genes[:max_results]]


def _get_gene_model(gene, field):
    # prefetching only works with all()
    return next((model for model in getattr(gene, '{}_set'.format(field)).all()), None)

def _add_gene_model(field, return_key, default):
    def _add_gene_model_func(gene):
        model = _get_gene_model(gene, field)
        return {return_key: _get_json_for_model(model) if model else default()}
    return _add_gene_model_func

def _add_dbnsfp(gene):
    model = _get_gene_model(gene, 'dbnsfpgene')
    if model:
        return _get_json_for_model(model)
    else:
        return _get_empty_json_for_model(dbNSFPGene)

def _add_omim(gene):
    omim_phenotypes = _get_json_for_models(gene.omim_set.all())
    return {
        'omimPhenotypes': [phenotype for phenotype in omim_phenotypes if phenotype['phenotypeMimNumber']],
        'mimNumber': omim_phenotypes[0]['mimNumber'] if omim_phenotypes else None,
    }

def _add_mgi(gene):
    model = _get_gene_model(gene, 'mgi')
    return {'mgiMarkerId': model.marker_id if model else None}

OMIM = 'omim'
CONSTRAINT = 'constraint'
CN_SENSITIVITY = 'cn_sensitivity'
SHET = 'shet'
DBNSFP = 'dbnsfp'
GENCC = 'gencc'
PRIMATE_AI = 'primate_ai'
MGI_FIELD = 'mgi'
CLINGEN = 'clingen'
NOTES= 'notes'
VARIANT_GENE_DISPLAY_FIELDS = {
    OMIM: (Omim, _add_omim),
    CONSTRAINT: (GeneConstraint, None),
    CN_SENSITIVITY: (GeneCopyNumberSensitivity, _add_gene_model('genecopynumbersensitivity', 'cnSensitivity', dict)),
    SHET: (GeneShet, _add_gene_model('geneshet', 'sHet', dict)),
    GENCC: (GenCC, _add_gene_model('gencc', 'genCc', dict)),
    CLINGEN: (ClinGen, _add_gene_model('clingen', 'clinGen', lambda: None)),
}
VARIANT_GENE_FIELDS = {
    DBNSFP: (dbNSFPGene, _add_dbnsfp),
    PRIMATE_AI: (PrimateAI, _add_gene_model('primateai', 'primateAi', lambda: None)),
}
VARIANT_GENE_FIELDS.update(VARIANT_GENE_DISPLAY_FIELDS)
ALL_GENE_FIELDS = {
    MGI_FIELD: (MGI, _add_mgi),
    NOTES: (None, None),
}
ALL_GENE_FIELDS.update(VARIANT_GENE_FIELDS)

def _get_json_for_genes(genes, user=None, gene_fields=None):
    if not gene_fields:
        gene_fields = {}

    total_gene_constraints = None
    if CONSTRAINT in gene_fields:
        total_gene_constraints = GeneConstraint.objects.count()

    if NOTES in gene_fields:
        gene_notes_json = get_json_for_gene_notes_by_gene_id([gene.gene_id for gene in genes], user)

    def _add_total_constraint_count(result, *args):
        result['totalGenes'] = total_gene_constraints

    def _process_result(result, gene):
        for field, (_, result_func) in gene_fields.items():
            if field == NOTES:
                updates = {'notes': gene_notes_json.get(result['geneId'], [])}
            elif field ==  CONSTRAINT:
                constraint = _get_gene_model(gene, 'geneconstraint')
                updates = {'constraints':  _get_json_for_model(constraint, process_result=_add_total_constraint_count) if constraint else {}}
            else:
                updates = result_func(gene)
            result.update(updates)

    for model, _ in gene_fields.values():
        if model:
            prefetch_related_objects(genes, Prefetch(
                '{}_set'.format(model.__name__.lower()),
                queryset=model.objects.only('gene__gene_id', *model._meta.json_fields)))

    return _get_json_for_models(genes, process_result=_process_result)


def parse_locus_list_items(request_json):
    raw_items = request_json.get('rawItems')
    if not raw_items:
        return None, None, None

    invalid_items = []
    intervals = []
    gene_ids = set()
    gene_symbols = set()
    for item in raw_items.replace(',', ' ').replace('\t', '<TAB>').split():
        interval_match = re.match('(?P<chrom>\w+):(?P<start>\d+)-(?P<end>\d+)(%(?P<offset>(\d+)))?', item)
        if not interval_match:
            interval_match = re.match('(?P<chrom>\w+)<TAB>(?P<start>\d+)<TAB>(?P<end>\d+)', item)
        if interval_match:
            interval = interval_match.groupdict()
            try:
                interval['chrom'] = interval['chrom'].lstrip('chr')
                interval['start'] = int(interval['start'])
                interval['end'] = int(interval['end'])
                if interval.get('offset'):
                    interval['offset'] = int(interval['offset']) / 100
                if interval['start'] > interval['end']:
                    raise ValueError
                get_xpos(interval['chrom'], interval['start'])
                get_xpos(interval['chrom'], interval['end'])
                intervals.append(interval)
            except (KeyError, ValueError):
                invalid_items.append('chr{chrom}:{start}-{end}'.format(
                    chrom=interval.get('chrom'), start=interval.get('start'), end=interval.get('end')
                ))
        elif item.upper().startswith('ENSG'):
            gene_ids.add(item.replace('<TAB>', ''))
        else:
            gene_symbols.add(item.replace('<TAB>', ''))

    gene_symbols_to_ids = get_gene_ids_for_gene_symbols(gene_symbols)
    invalid_items += [symbol for symbol in gene_symbols if not gene_symbols_to_ids.get(symbol)]
    gene_ids.update({gene_ids[0] for gene_ids in gene_symbols_to_ids.values() if len(gene_ids)})
    genes_by_id = get_genes(list(gene_ids)) if gene_ids else {}
    invalid_items += [gene_id for gene_id in gene_ids if not genes_by_id.get(gene_id)]
    return genes_by_id, intervals, invalid_items