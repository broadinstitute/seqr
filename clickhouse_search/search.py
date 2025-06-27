from clickhouse_backend.models import ArrayField, StringField
from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Min
from django.db.models.functions import JSONObject

from clickhouse_search.backend.fields import NamedTupleField
from clickhouse_search.backend.functions import Array, ArrayFilter, ArrayIntersect, ArraySort, Tuple
from clickhouse_search.models import ENTRY_CLASS_MAP, ANNOTATIONS_CLASS_MAP, TRANSCRIPTS_CLASS_MAP, BaseClinvar, \
    BaseAnnotationsMitoSnvIndel, BaseAnnotationsGRCh37SnvIndel
from reference_data.models import GeneConstraint, Omim
from seqr.models import PhenotypePrioritization
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.search.constants import MAX_VARIANTS, XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY, \
    PRIORITIZED_GENE_SORT, COMPOUND_HET, RECESSIVE
from settings import CLICKHOUSE_SERVICE_HOSTNAME

logger = SeqrLogger(__name__)


TRANSCRIPT_CONSEQUENCES_FIELD = 'sortedTranscriptConsequences'
SELECTED_GENE_FIELD = 'selectedGeneId'
SELECTED_TRANSCRIPT_FIELD = 'selectedTranscript'


def clickhouse_backend_enabled():
    return bool(CLICKHOUSE_SERVICE_HOSTNAME)


def get_clickhouse_variants(samples, search, user, previous_search_results, genome_version,page=1, num_results=100, sort=None, **kwargs):
    sample_data_by_dataset_type = _get_sample_data(samples)
    results = []
    family_guid = None
    inheritance_mode = search.get('inheritance_mode')
    for dataset_type, sample_data in sample_data_by_dataset_type.items():
        logger.info(f'Loading {dataset_type} data for {len(sample_data)} families', user)

        entry_cls = ENTRY_CLASS_MAP[genome_version][dataset_type]
        annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][dataset_type]
        family_guid = sample_data[0]['family_guid']

        if inheritance_mode != COMPOUND_HET:
            result_q = _get_search_results_queryset(entry_cls, annotations_cls, search, sample_data)
            results += list(result_q[:MAX_VARIANTS + 1])
        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            result_q = _get_comp_het_results_queryset(entry_cls, annotations_cls, search, sample_data)
            results += [list(result[1:]) for result in result_q[:MAX_VARIANTS + 1]]

    cache_results = get_clickhouse_cache_results(results, sort, family_guid)
    previous_search_results.update(cache_results)

    logger.info(f'Total results: {cache_results["total_results"]}', user)

    return format_clickhouse_results(cache_results['all_results'][(page-1)*num_results:page*num_results], genome_version)


def _get_search_results_queryset(entry_cls, annotations_cls, search, sample_data):
    entries = entry_cls.objects.search(sample_data, **search)
    results = annotations_cls.objects.subquery_join(entries).search(**search)
    return results.result_values()


def _get_comp_het_results_queryset(entry_cls, annotations_cls, search, sample_data):
    entries = entry_cls.objects.search(
        sample_data, **{**search, 'inheritance_mode': COMPOUND_HET}, annotate_carriers=True,
    )

    primary_q = annotations_cls.objects.subquery_join(entries).search(**search)

    annotations_secondary = search.get('annotations_secondary')
    secondary_search = {**search, 'annotations': annotations_secondary} if annotations_secondary else search
    secondary_q = annotations_cls.objects.subquery_join(entries).search(**secondary_search)

    carrier_field = next((field for field in ['family_carriers', 'carriers'] if field in entries.query.annotations), None)

    results = annotations_cls.objects.search_compound_hets(primary_q, secondary_q, carrier_field)

    if carrier_field == 'carriers':
        results = results.annotate(
            unphased_carriers=ArrayIntersect('primary_carriers', 'secondary_carriers')
        ).filter(unphased_carriers__not_empty=False)
    elif carrier_field == 'family_carriers':
        results = results.annotate(
            primary_familyGuids=ArrayFilter('primary_familyGuids', conditions=[
                {None: (None, 'empty(arrayIntersect(primary_family_carriers[x], secondary_family_carriers[x]))')},
            ]),
        )

    if len(sample_data) > 1:
        results = results.annotate(
            primary_familyGuids=ArrayIntersect(
                'primary_familyGuids', 'secondary_familyGuids', output_field=ArrayField(StringField()),
            ),
        ).filter(primary_familyGuids__not_empty=True).annotate(
            secondary_familyGuids=F('primary_familyGuids'),
            primary_genotypes=ArrayFilter('primary_genotypes', conditions=[
                {2: ('arrayIntersect(primary_familyGuids, secondary_familyGuids)', 'has({value}, {field})')},
            ]),
            secondary_genotypes=ArrayFilter('secondary_genotypes', conditions=[
                {2: ('arrayIntersect(primary_familyGuids, secondary_familyGuids)', 'has({value}, {field})')},
            ]),
        )

    return results.annotate(
        pair_key=ArraySort(Array('primary_key', 'secondary_key')),
    ).distinct('pair_key').values_list(
        'pair_key',
        _result_as_tuple(results, 'primary_'),
        _result_as_tuple(results, 'secondary_'),
    )

def _result_as_tuple(results, field_prefix):
    fields = {
        name: (name.replace(field_prefix, ''), getattr(col, 'target', col.output_field)) for name, col in results.query.annotations.items()
        if name.startswith(field_prefix) and not name.endswith('carriers')
    }
    return Tuple(*fields.keys(), output_field=NamedTupleField(list(fields.values())))


def get_clickhouse_cache_results(results, sort, family_guid):
    sort_metadata = _get_sort_gene_metadata(sort, results, family_guid)
    sort_key = _get_sort_key(sort, sort_metadata)
    sorted_results = sorted([
        sorted(result, key=sort_key) if isinstance(result, list) else result for result in results
    ], key=sort_key)
    total_results = len(sorted_results)
    return {'all_results': sorted_results, 'total_results': total_results}


def format_clickhouse_results(results, genome_version, **kwargs):
    keys_with_transcripts = {
        variant['key'] for result in results for variant in (result if isinstance(result, list) else [result]) if not 'transcripts' in variant
    }
    transcripts_by_key = dict(
        TRANSCRIPTS_CLASS_MAP[genome_version].objects.filter(key__in=keys_with_transcripts).values_list('key', 'transcripts')
    )

    formatted_results = []
    for variant in results:
        if isinstance(variant, list):
            formatted_result = [_format_variant(v, transcripts_by_key) for v in variant]
        else:
            formatted_result = _format_variant(variant, transcripts_by_key)
        formatted_results.append(formatted_result)

    return formatted_results


def _format_variant(variant, transcripts_by_key):
    if 'transcripts' in variant:
        return variant

    transcripts = transcripts_by_key.get(variant['key'], {})
    formatted_variant = {
        **variant,
        'transcripts': transcripts,
    }
    # pop sortedTranscriptConsequences from the formatted result and not the original result to ensure the full value is cached properly
    sorted_minimal_transcripts = formatted_variant.pop(TRANSCRIPT_CONSEQUENCES_FIELD)
    selected_gene_id = formatted_variant.pop(SELECTED_GENE_FIELD, None)
    selected_transcript = formatted_variant.pop(SELECTED_TRANSCRIPT_FIELD, None)
    main_transcript_id = None
    selected_main_transcript_id = None
    if sorted_minimal_transcripts:
        main_transcript_id = next(
            t['transcriptId'] for t in transcripts[sorted_minimal_transcripts[0]['geneId']]
            if t['transcriptRank'] == 0
        )
    if selected_transcript:
        selected_main_transcript_id = next(
            t['transcriptId'] for t in transcripts[selected_transcript['geneId']]
            if _is_matched_minimal_transcript(t, selected_transcript)
        )
    elif selected_gene_id:
        selected_main_transcript_id = transcripts[selected_gene_id][0]['transcriptId']
    return {
        **formatted_variant,
        'mainTranscriptId': main_transcript_id,
        'selectedMainTranscriptId': None if selected_main_transcript_id == main_transcript_id else selected_main_transcript_id,
    }


def _is_matched_minimal_transcript(transcript, minimal_transcript):
    return (all(transcript[field] == minimal_transcript[field] for field in ['canonical','consequenceTerms'])
     and transcript.get('utrannotator', {}).get('fiveutrConsequence') == minimal_transcript.get('fiveutrConsequence')
     and transcript.get('spliceregion', {}).get('extended_intronic_splice_region_variant') == minimal_transcript.get('extendedIntronicSpliceRegionVariant'))



def _get_sample_data(samples):
    sample_data = samples.values(
        'dataset_type', family_guid=F('individual__family__guid'), project_guid=F('individual__family__project__guid'),
    ).annotate(
        samples=ArrayAgg(JSONObject(affected='individual__affected', sex='individual__sex', sample_id='sample_id', sample_type='sample_type', individual_guid=F('individual__guid'))),
        sample_types=ArrayAgg('sample_type', distinct=True),
    )
    samples_by_dataset_type = defaultdict(list)
    for data in sample_data:
        samples_by_dataset_type[data['dataset_type']].append({**data, 'samples': _group_by_sample_type(data['samples'])})
    return samples_by_dataset_type


def _group_by_sample_type(samples):
    samples_by_individual_type = {}
    for sample in samples:
        sample_type = sample.pop('sample_type')
        sample_id = sample.pop('sample_id')
        if sample['individual_guid'] not in samples_by_individual_type:
            samples_by_individual_type[sample['individual_guid']] = {'sample_ids_by_type': {}, **sample}
        samples_by_individual_type[sample['individual_guid']]['sample_ids_by_type'][sample_type] = sample_id
    return list(samples_by_individual_type.values())


OMIM_SORT = 'in_omim'
GENE_SORTS = {
    'constraint': lambda gene_ids, _: {
        agg['gene__gene_id']: agg['mis_z_rank'] + agg['pLI_rank'] for agg in
        GeneConstraint.objects.filter(gene__gene_id__in=gene_ids).values('gene__gene_id', 'mis_z_rank', 'pLI_rank')
    },
    OMIM_SORT: lambda gene_ids, _: set(Omim.objects.filter(
        gene__gene_id__in=gene_ids, phenotype_mim_number__isnull=False,
    ).values_list('gene__gene_id', flat=True)),
    PRIORITIZED_GENE_SORT: lambda gene_ids, family_guid: {
        agg['gene_id']: agg['min_rank'] for agg in PhenotypePrioritization.objects.filter(
            gene_id__in=gene_ids, individual__family__guid=family_guid, rank__lte=100,
        ).values('gene_id').annotate(min_rank=Min('rank'))
    },
}

def _get_sort_gene_metadata(sort, results, family_guid):
    get_metadata = GENE_SORTS.get(sort)
    if not get_metadata:
        return None

    gene_ids = set()
    for result in results:
        gene_ids.update([t['geneId'] for t in result.get(TRANSCRIPT_CONSEQUENCES_FIELD, [])])
    return get_metadata(gene_ids, family_guid)


MAX_SORT_RANK = 1e10
def _subfield_sort(*fields, rank_lookup=None, default=MAX_SORT_RANK, reverse=False):
    def _sort(item):
        for field in fields:
            if isinstance(field, tuple):
                field = next((f for f in field if f in item), None)
            item = (item or {}).get(field)
        if rank_lookup:
            item = rank_lookup.get(item)
        value = default if item is None else item
        return value if not reverse else -value
    return [_sort]


def _get_matched_transcript(x, field):
    if field not in x:
        return None
    for transcripts in x['transcripts'].values():
        transcript = next((t for t in transcripts if t['transcriptId'] == x[field]), None)
        if transcript:
            return transcript
    return None


def _main_transcript_consequence(x):
    transcript = x[TRANSCRIPT_CONSEQUENCES_FIELD][0] if x.get(TRANSCRIPT_CONSEQUENCES_FIELD) else _get_matched_transcript(x, 'mainTranscriptId')
    return CONSEQUENCE_RANK_LOOKUP[transcript['consequenceTerms'][0]] if transcript else MAX_SORT_RANK

def _selected_transcript_consequence(x):
    transcript = x.get(SELECTED_TRANSCRIPT_FIELD) or _get_matched_transcript(x, 'selectedMainTranscriptId')
    return CONSEQUENCE_RANK_LOOKUP[transcript['consequenceTerms'][0]] if transcript else MAX_SORT_RANK

MIN_SORT_RANK = 0
MIN_PRED_SORT_RANK = -1
CLINVAR_RANK_LOOKUP = {path: rank for rank, path in BaseClinvar.PATHOGENICITY_CHOICES}
HGMD_RANK_LOOKUP = {class_: rank for rank, class_ in BaseAnnotationsGRCh37SnvIndel.HGMD_CLASSES}
ABSENT_CLINVAR_SORT_OFFSET = 12.5
CONSEQUENCE_RANK_LOOKUP = {csq: rank for rank, csq in BaseAnnotationsMitoSnvIndel.CONSEQUENCE_TERMS}
PREDICTION_SORTS = {'cadd', 'revel', 'splice_ai', 'eigen', 'mpc', 'primate_ai'}
CLINVAR_SORT =  _subfield_sort(
    'clinvar', 'pathogenicity', rank_lookup=CLINVAR_RANK_LOOKUP, default=ABSENT_CLINVAR_SORT_OFFSET,
)
SORT_EXPRESSIONS = {
    'alphamissense': [
        lambda x: -max(t.get('alphamissensePathogenicity') or MIN_SORT_RANK for t in x[TRANSCRIPT_CONSEQUENCES_FIELD]) if x.get(TRANSCRIPT_CONSEQUENCES_FIELD) else MIN_SORT_RANK,
    ] + _subfield_sort(SELECTED_TRANSCRIPT_FIELD, 'alphamissensePathogenicity', reverse=True, default=MIN_SORT_RANK),
    'callset_af': _subfield_sort('populations', 'seqr', 'ac'),
    'family_guid': [lambda x: sorted(x['familyGuids'])[0]],
    'gnomad': _subfield_sort('populations', ('gnomad_genomes', 'gnomad_mito'), 'af'),
    'gnomad_exomes': _subfield_sort('populations', 'gnomad_exomes', 'af'),
    PATHOGENICTY_SORT_KEY: CLINVAR_SORT,
    PATHOGENICTY_HGMD_SORT_KEY: CLINVAR_SORT + _subfield_sort('hgmd', 'class', rank_lookup=HGMD_RANK_LOOKUP),
    'protein_consequence': [_main_transcript_consequence, _selected_transcript_consequence],
    **{sort: _subfield_sort('predictions', sort, reverse=True, default=MIN_PRED_SORT_RANK) for sort in PREDICTION_SORTS},
}

def _get_sort_key(sort, gene_metadata):
    sort_expressions = SORT_EXPRESSIONS.get(sort, [])

    if sort == OMIM_SORT:
        sort_expressions = [
            lambda x: 0 if ((x.get(SELECTED_TRANSCRIPT_FIELD) or {}).get('geneId') or x.get(SELECTED_GENE_FIELD)) in gene_metadata else 1,
            lambda x: -len(set(t['geneId'] for t in x.get(TRANSCRIPT_CONSEQUENCES_FIELD, []) if t['geneId'] in gene_metadata)),
        ]
    elif gene_metadata:
        sort_expressions = [
            lambda x: gene_metadata.get((x.get(SELECTED_TRANSCRIPT_FIELD) or {}).get('geneId') or x.get(SELECTED_GENE_FIELD), MAX_SORT_RANK),
            lambda x: min([gene_metadata[t['geneId']] for t in x.get(TRANSCRIPT_CONSEQUENCES_FIELD, []) if t['geneId'] in gene_metadata] or [MAX_SORT_RANK]),
        ]

    return lambda x: tuple(expr(x[0] if isinstance(x, list) else x) for expr in [*sort_expressions, lambda x: x[XPOS_SORT_KEY]])
