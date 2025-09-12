from clickhouse_backend.models import ArrayField, StringField
from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections
from django.db.models import F, Min, Q
from django.db.models.functions import JSONObject
import json

from clickhouse_search.backend.fields import NamedTupleField
from clickhouse_search.backend.functions import Array, ArrayFilter, ArrayIntersect, ArraySort, GroupArrayArray, If, Tuple, \
    ArrayDistinct, ArrayMap
from clickhouse_search.models import ENTRY_CLASS_MAP, ANNOTATIONS_CLASS_MAP, TRANSCRIPTS_CLASS_MAP, KEY_LOOKUP_CLASS_MAP, \
    BaseClinvar, BaseAnnotationsMitoSnvIndel, BaseAnnotationsGRCh37SnvIndel, BaseAnnotationsSvGcnv
from reference_data.models import GeneConstraint, Omim, GENOME_VERSION_LOOKUP
from seqr.models import Sample, PhenotypePrioritization, Individual
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.search.constants import MAX_VARIANTS, XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY, \
    PRIORITIZED_GENE_SORT, COMPOUND_HET, COMPOUND_HET_ALLOW_HOM_ALTS, RECESSIVE
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets
from settings import CLICKHOUSE_SERVICE_HOSTNAME

logger = SeqrLogger(__name__)

BATCH_SIZE = 10000

TRANSCRIPT_CONSEQUENCES_FIELD = 'sortedTranscriptConsequences'
SELECTED_GENE_FIELD = 'selectedGeneId'
SELECTED_TRANSCRIPT_FIELD = 'selectedTranscript'


def get_clickhouse_variants(samples, search, user, previous_search_results, genome_version,page=1, num_results=100, sort=None, **kwargs):
    sample_data_by_dataset_type = _get_sample_data(samples)
    results = []
    family_guid = None
    inheritance_mode = search.get('inheritance_mode')
    has_comp_het = inheritance_mode in {RECESSIVE, COMPOUND_HET}
    for dataset_type, sample_data in sample_data_by_dataset_type.items():
        logger.info(f'Loading {dataset_type} data for {len(set(sample_data["family_guids"]))} families', user)

        entry_cls = ENTRY_CLASS_MAP[genome_version][dataset_type]
        annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][dataset_type]
        family_guid = sample_data['family_guids'][0]
        is_multi_project = len(sample_data['project_guids']) > 1

        dataset_results = []
        if inheritance_mode != COMPOUND_HET:
            result_q = _get_search_results_queryset(entry_cls, annotations_cls, sample_data, skip_individual_guid=is_multi_project, **search)
            dataset_results += _evaluate_results(result_q)
        if has_comp_het:
            comp_het_sample_data = sample_data
            if is_multi_project and dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS and _is_x_chrom_only(**search):
                comp_het_sample_data = _no_affected_male_families(sample_data, user)
            result_q = _get_data_type_comp_het_results_queryset(entry_cls, annotations_cls, comp_het_sample_data, skip_individual_guid=is_multi_project, **search)
            dataset_results += _evaluate_results(result_q, is_comp_het=True)

        if is_multi_project:
            _add_individual_guids(dataset_results, sample_data)
        results += dataset_results

    if has_comp_het and Sample.DATASET_TYPE_VARIANT_CALLS in sample_data_by_dataset_type and any(
        dataset_type.startswith(Sample.DATASET_TYPE_SV_CALLS) for dataset_type in sample_data_by_dataset_type
    ):
        results += _get_multi_data_type_comp_het_results_queryset(genome_version, sample_data_by_dataset_type, user, **search)

    cache_results = get_clickhouse_cache_results(results, sort, family_guid)
    previous_search_results.update(cache_results)

    logger.info(f'Total results: {cache_results["total_results"]}', user)

    return format_clickhouse_results(cache_results['all_results'][(page-1)*num_results:page*num_results], genome_version)


def _get_search_results_queryset(entry_cls, annotations_cls, sample_data, **search_kwargs):
    entries = entry_cls.objects.search(sample_data, **search_kwargs)
    results = annotations_cls.objects.subquery_join(entries).search(**search_kwargs)
    return results.result_values()


def _evaluate_results(result_q, is_comp_het=False):
    results = [list(result[1:]) if is_comp_het else result for result in result_q[:MAX_VARIANTS + 1]]
    if len(results) > MAX_VARIANTS:
        from seqr.utils.search.utils import InvalidSearchException
        raise InvalidSearchException('This search returned too many results')
    return results

def _get_multi_data_type_comp_het_results_queryset(genome_version, sample_data_by_dataset_type, user, annotations=None, annotations_secondary=None, inheritance_mode=None, **search_kwargs):
    if annotations_secondary:
        annotations = {
            **annotations,
            **{k: v + annotations[k] if k in annotations else v for k, v in annotations_secondary.items()},
        }

    entry_cls = ENTRY_CLASS_MAP[genome_version][Sample.DATASET_TYPE_VARIANT_CALLS]
    annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][Sample.DATASET_TYPE_VARIANT_CALLS]
    snv_indel_sample_data = sample_data_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS]
    snv_indel_families = set(snv_indel_sample_data['family_guids'])
    skip_individual_guid = len(snv_indel_sample_data['project_guids']) > 1

    results = []
    for sample_type in [Sample.SAMPLE_TYPE_WES, Sample.SAMPLE_TYPE_WGS]:
        sv_dataset_type = f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}'
        sv_sample_data = sample_data_by_dataset_type.get(sv_dataset_type, {})
        sv_families = set(sv_sample_data.get('family_guids', []))
        families = snv_indel_families.intersection(sv_families)
        if not families:
            continue
        logger.info(f'Loading {Sample.DATASET_TYPE_VARIANT_CALLS}/{sv_dataset_type} data for {len(families)} families', user)

        entries = entry_cls.objects.search({
            **snv_indel_sample_data,
            'family_guids': list(families),
            'samples': [s for s in snv_indel_sample_data['samples'] if s['family_guid'] in families]
        }, skip_individual_guid=skip_individual_guid, **search_kwargs, annotations=annotations, inheritance_mode=COMPOUND_HET_ALLOW_HOM_ALTS, annotate_carriers=True, annotate_hom_alts=True)
        snv_indel_q = annotations_cls.objects.subquery_join(entries).search(**search_kwargs, annotations=annotations)

        sv_sample_data = {
            **sv_sample_data,
            'family_guids': list(families),
            'samples': [s for s in sv_sample_data['samples'] if s['family_guid'] in families]
        }
        sv_entries = ENTRY_CLASS_MAP[genome_version][sv_dataset_type].objects.search(
            sv_sample_data, **search_kwargs, annotations=annotations, inheritance_mode=COMPOUND_HET, annotate_carriers=True,
        )
        sv_annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][sv_dataset_type]
        sv_q = sv_annotations_cls.objects.subquery_join(sv_entries).search(**search_kwargs, annotations=annotations)

        result_q = _get_comp_het_results_queryset(annotations_cls, snv_indel_q, sv_q, len(families))
        dataset_results = _evaluate_results(result_q, is_comp_het=True)
        if skip_individual_guid:
            _add_individual_guids(dataset_results, sv_sample_data)
        results += dataset_results

    return results


def _get_data_type_comp_het_results_queryset(entry_cls, annotations_cls, sample_data, annotations=None, annotations_secondary=None, inheritance_mode=None, **search_kwargs):
    entries = entry_cls.objects.search(
        sample_data, **search_kwargs, inheritance_mode=COMPOUND_HET, annotations=annotations, annotate_carriers=True,
    )

    primary_q = annotations_cls.objects.subquery_join(entries).search(annotations=annotations, **search_kwargs)
    secondary_q = annotations_cls.objects.subquery_join(entries).search(
        annotations=annotations_secondary or annotations, **search_kwargs,
    )

    return _get_comp_het_results_queryset(annotations_cls, primary_q, secondary_q, len(set(sample_data['family_guids'])))


def _get_comp_het_results_queryset(annotations_cls, primary_q, secondary_q, num_families):
    results = annotations_cls.objects.search_compound_hets(primary_q, secondary_q)

    if results.has_annotation('primary_carriers') and results.has_annotation('secondary_carriers'):
        results = results.annotate(
            unphased_carriers=ArrayIntersect('primary_carriers', 'secondary_carriers')
        ).filter(unphased_carriers__not_empty=False)
    elif results.has_annotation('primary_family_carriers') and results.has_annotation('secondary_family_carriers'):
        results = results.annotate(
            primary_familyGuids=ArrayFilter('primary_familyGuids', conditions=[
                {None: (None, 'empty(arrayIntersect(primary_family_carriers[x], secondary_family_carriers[x]))')},
            ]),
        )

    if results.has_annotation('primary_has_hom_alt') or results.has_annotation('primary_no_hom_alt_families'):
        is_overlapped_del = Q(secondary_svType='DEL', primary_pos__gte=F('secondary_pos'),  primary_pos__lte=F('secondary_end'))
        if results.has_annotation('primary_has_hom_alt'):
            results = results.filter(is_overlapped_del | Q(primary_has_hom_alt=False))
        else:
            results = results.annotate(primary_familyGuids=If(
                is_overlapped_del,
                F('primary_familyGuids'),
                ArrayIntersect('primary_familyGuids', 'primary_no_hom_alt_families'),
                condition='', output_field=ArrayField(StringField()),
            ))

    if num_families > 1:
        primary_family_expr = 'primary_familyGuids' if results.has_annotation('primary_familyGuids') else ArrayMap(
            'primary_familyGenotypes', mapped_expression='x.1',
        )
        secondary_family_expr = 'secondary_familyGuids' if results.has_annotation('secondary_familyGuids') else ArrayMap(
            'secondary_familyGenotypes', mapped_expression='x.1',
        )
        if results.has_annotation('primary_genotypes'):
            genotype_expressions = {
                'primary_genotypes': ArrayFilter('primary_genotypes', conditions=[
                    {2: ('arrayIntersect(primary_familyGuids, secondary_familyGuids)', 'has({value}, {field})')},
                ]),
                'secondary_genotypes': ArrayFilter('secondary_genotypes', conditions=[
                    {2: ('arrayIntersect(primary_familyGuids, secondary_familyGuids)', 'has({value}, {field})')},
                ]),
            }
        elif results.has_annotation('secondary_genotypes'):
            genotype_expressions = {
                'primary_familyGenotypes': ArrayFilter('primary_familyGenotypes', conditions=[
                    {1: ('secondary_familyGuids', 'has({value}, {field})')},
                ]),
                'secondary_genotypes': ArrayFilter('secondary_genotypes', conditions=[
                    {2: (None, 'arrayExists(g -> g.1 = {field}, primary_familyGenotypes)')},
                ]),
            }
        else:
            genotype_expressions = {
                'primary_familyGenotypes': ArrayFilter('primary_familyGenotypes', conditions=[
                    {1: (None, 'arrayExists(g -> g.1 = {field}, secondary_familyGenotypes)')},
                ]),
                'secondary_familyGenotypes': ArrayFilter('secondary_familyGenotypes', conditions=[
                    {1: (None, 'arrayExists(g -> g.1 = {field}, primary_familyGenotypes)')},
                ]),
            }
        results = results.annotate(
            primary_familyGuids=ArrayIntersect(
                primary_family_expr, secondary_family_expr, output_field=ArrayField(StringField()),
            ),
        ).filter(primary_familyGuids__not_empty=True).annotate(
            secondary_familyGuids=F('primary_familyGuids'),
            **genotype_expressions,
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
        if name.startswith(field_prefix) and not name.endswith('carriers') and not 'hom_alt' in name
    }
    return Tuple(*fields.keys(), output_field=NamedTupleField(list(fields.values())))


def _add_individual_guids(results, sample_data):
    sample_map = {(s['family_guid'], s['sample_id']): s['individual_guid'] for s in sample_data['samples']}
    for result in results:
        if isinstance(result, list):
            for variant in result:
                _set_individual_guids(variant, sample_map)
        else:
            _set_individual_guids(result, sample_map)


def _set_individual_guids(result, sample_map):
    if 'familyGenotypes' not in result:
        return
    result['familyGuids'] = sorted(result['familyGenotypes'].keys())
    individual_genotypes =  defaultdict(list)
    for family_guid, genotypes in result.pop('familyGenotypes').items():
        for genotype in genotypes:
            individual_guid = sample_map[(family_guid, genotype['sampleId'])]
            individual_genotypes[individual_guid].append({**genotype, 'individualGuid': individual_guid})
    result['genotypes'] = {k: v[0] if len(v) == 1 else v for k, v in individual_genotypes.items()}


def get_clickhouse_cache_results(results, sort, family_guid):
    sort_metadata = _get_sort_gene_metadata(sort, results, family_guid)
    sort_key = _get_sort_key(sort, sort_metadata)
    sorted_results = sorted([
        sorted(result, key=sort_key) if isinstance(result, list) else result for result in results
    ], key=sort_key)
    total_results = len(sorted_results)
    return {'all_results': sorted_results, 'total_results': total_results}


def get_transcripts_queryset(genome_version, keys):
    return TRANSCRIPTS_CLASS_MAP[genome_version].objects.filter(key__in=keys)


def get_transcripts_by_key(genome_version, keys):
    return dict(get_transcripts_queryset(genome_version, keys).values_list('key', 'transcripts'))


def format_clickhouse_results(results, genome_version, **kwargs):
    keys_with_transcripts = {
        variant['key'] for result in results for variant in (result if isinstance(result, list) else [result]) if not 'transcripts' in variant
    }
    transcripts_by_key = get_transcripts_by_key(genome_version, keys_with_transcripts)

    formatted_results = []
    for variant in results:
        if isinstance(variant, list):
            formatted_result = [_format_variant(v, transcripts_by_key) for v in variant]
        else:
            formatted_result = _format_variant(variant, transcripts_by_key)
        formatted_results.append(formatted_result)

    return formatted_results


def _format_variant(variant, transcripts_by_key):
    formatted_variant = {**variant}
    selected_gene_id = formatted_variant.pop(SELECTED_GENE_FIELD, None)
    selected_transcript = formatted_variant.pop(SELECTED_TRANSCRIPT_FIELD, None)
    if 'transcripts' in variant:
        return formatted_variant

    transcripts = transcripts_by_key.get(variant['key'], {})
    formatted_variant['transcripts'] = transcripts
    # pop sortedTranscriptConsequences from the formatted result and not the original result to ensure the full value is cached properly
    sorted_minimal_transcripts = formatted_variant.pop(TRANSCRIPT_CONSEQUENCES_FIELD)
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
    mismatch_affected_samples = samples.values('sample_id', 'dataset_type').annotate(
        projects=ArrayAgg('individual__family__project__name', distinct=True),
        affected=ArrayAgg('individual__affected', distinct=True),
    ).filter(affected__len__gt=1)
    if mismatch_affected_samples:
        from seqr.utils.search.utils import InvalidSearchException
        raise InvalidSearchException(
            'The following samples are incorrectly configured and have different affected statuses in different projects: ' +
            ', '.join([f'{agg["sample_id"]} ({"/ ".join(agg["projects"])})' for agg in mismatch_affected_samples]),
        )

    sample_data = samples.values(
        'dataset_type', 'sample_type',
    ).annotate(
        project_guids=ArrayAgg('individual__family__project__guid', distinct=True),
        family_guids=ArrayAgg('individual__family__guid', distinct=True),
        samples=ArrayAgg(JSONObject(affected='individual__affected', sex='individual__sex', sample_id='sample_id', sample_type='sample_type', family_guid=F('individual__family__guid'), individual_guid=F('individual__guid'))),
    )
    samples_by_dataset_type = {}
    for data in sample_data:
        dataset_type = data.pop('dataset_type')
        sample_type = data.pop('sample_type')
        if dataset_type == Sample.DATASET_TYPE_SV_CALLS:
            dataset_type = f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}'

        if dataset_type in samples_by_dataset_type:
            other_type_data = samples_by_dataset_type[dataset_type]
            other_sample_type = next(iter(other_type_data['sample_type_families'].keys()))
            family_guids = set(data['family_guids'])
            other_type_family_guids = set(other_type_data['family_guids'])
            sample_type_families = {
                other_sample_type: other_type_family_guids - family_guids,
                sample_type: family_guids - other_type_family_guids,
                'multi': family_guids.intersection(other_type_family_guids),
            }
            data['sample_type_families'] = {k: v for k, v in sample_type_families.items() if v}
            for key in ['project_guids', 'family_guids', 'samples']:
                data[key] += other_type_data[key]
        else:
            data['sample_type_families'] = {sample_type: set(data['family_guids'])}

        samples_by_dataset_type[dataset_type] = data
    return samples_by_dataset_type


def _no_affected_male_families(sample_data, user):
    valid_families = {
        s['family_guid'] for s in sample_data['samples']
        if s['affected'] == Individual.AFFECTED_STATUS_AFFECTED and s['sex'] != Individual.SEX_MALE
    }
    logger.info(f'Loading X-chromosome compound het data for {len(valid_families)} families', user)
    return {
        **sample_data,
        'family_guids': list(valid_families),
        'samples': [s for s in sample_data['samples'] if s['family_guid'] in valid_families],
    }


def _is_x_chrom_only(parsed_locus=None, **kwargs):
    parsed_locus = parsed_locus or {}
    all_intervals = list((parsed_locus.get('gene_intervals') or {}).values()) + (parsed_locus.get('intervals') or [])
    return bool(all_intervals) and all('X' in interval[0] for interval in all_intervals)


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
        if not isinstance(result, list):
            result = [result]
        for variant in result:
            if variant.get(TRANSCRIPT_CONSEQUENCES_FIELD):
                gene_ids.update([t['geneId'] for t in variant[TRANSCRIPT_CONSEQUENCES_FIELD]])
            else:
                gene_ids.update(variant.get('transcripts', {}).keys())
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


def _consequence_sort(get_transcript, transcript_field, get_sv_rank):
    def wrapped_sort(x):
        if x.get('svType'):
            return get_sv_rank(x)
        transcript = get_transcript(x) or _get_matched_transcript(x, transcript_field)
        return CONSEQUENCE_RANK_LOOKUP[transcript['consequenceTerms'][0]] if transcript else MAX_SORT_RANK
    return wrapped_sort

def _sv_size(x):
    if not x.get('end'):
        return -1
    if x.get('endChrom'):
        # Sort position for chromosome spanning SVs
        return -50
    return x['pos'] - x['end']

MIN_SORT_RANK = 0
MIN_PRED_SORT_RANK = -1
CLINVAR_RANK_LOOKUP = {path: rank for rank, path in BaseClinvar.PATHOGENICITY_CHOICES}
HGMD_RANK_LOOKUP = {class_: rank for rank, class_ in BaseAnnotationsGRCh37SnvIndel.HGMD_CLASSES}
ABSENT_CLINVAR_SORT_OFFSET = 12.5
CONSEQUENCE_RANK_LOOKUP = {csq: rank for rank, csq in BaseAnnotationsMitoSnvIndel.CONSEQUENCE_TERMS}
SV_CONSEQUENCE_LOOKUP = {csq: rank for rank, csq in BaseAnnotationsSvGcnv.SV_CONSEQUENCE_RANKS}
PREDICTION_SORTS = {'cadd', 'revel', 'splice_ai', 'eigen', 'mpc', 'primate_ai'}
CLINVAR_SORT =  _subfield_sort(
    'clinvar', 'pathogenicity', rank_lookup=CLINVAR_RANK_LOOKUP, default=ABSENT_CLINVAR_SORT_OFFSET,
)
SORT_EXPRESSIONS = {
    'alphamissense': [
        lambda x: -max(t.get('alphamissensePathogenicity') or MIN_SORT_RANK for t in x[TRANSCRIPT_CONSEQUENCES_FIELD]) if x.get(TRANSCRIPT_CONSEQUENCES_FIELD) else MIN_SORT_RANK,
    ] + _subfield_sort(SELECTED_TRANSCRIPT_FIELD, 'alphamissensePathogenicity', reverse=True, default=MIN_SORT_RANK),
    'callset_af': _subfield_sort('populations', ('seqr', 'sv_callset'), 'ac'),
    'family_guid': [lambda x: sorted(x['familyGuids'])[0]],
    'gnomad': _subfield_sort('populations', ('gnomad_genomes', 'gnomad_mito', 'gnomad_svs'), 'af'),
    'gnomad_exomes': _subfield_sort('populations', 'gnomad_exomes', 'af'),
    PATHOGENICTY_SORT_KEY: CLINVAR_SORT,
    PATHOGENICTY_HGMD_SORT_KEY: CLINVAR_SORT + _subfield_sort('hgmd', 'class', rank_lookup=HGMD_RANK_LOOKUP),
    'protein_consequence': [
        _consequence_sort(
            lambda x: (x.get(TRANSCRIPT_CONSEQUENCES_FIELD) or [None])[0],
            'mainTranscriptId',
            lambda x: 4.5,
        ),
        _consequence_sort(
            lambda x: x.get(SELECTED_TRANSCRIPT_FIELD),
            'selectedMainTranscriptId',
            lambda x: min([SV_CONSEQUENCE_LOOKUP[csqs[0]['majorConsequence']] for csqs in x['transcripts'].values()] or [MAX_SORT_RANK]),
        ),
    ],
    **{sort: _subfield_sort('predictions', sort, reverse=True, default=MIN_PRED_SORT_RANK) for sort in PREDICTION_SORTS},
    'size': [_sv_size],
}

def _get_sort_key(sort, gene_metadata):
    sort_expressions = SORT_EXPRESSIONS.get(sort, [])

    if sort == OMIM_SORT:
        sort_expressions = [
            lambda x: 0 if ((x.get(SELECTED_TRANSCRIPT_FIELD) or {}).get('geneId') or x.get(SELECTED_GENE_FIELD)) in gene_metadata else 1,
            lambda x: -len(
                set(t['geneId'] for t in x[TRANSCRIPT_CONSEQUENCES_FIELD] if t['geneId'] in gene_metadata)
                if x.get(TRANSCRIPT_CONSEQUENCES_FIELD) else set(x.get('transcripts', {}).keys()).intersection(gene_metadata)
            ),
        ]
    elif gene_metadata:
        sort_expressions = [
            lambda x: gene_metadata.get((x.get(SELECTED_TRANSCRIPT_FIELD) or {}).get('geneId') or x.get(SELECTED_GENE_FIELD), MAX_SORT_RANK),
            lambda x: min(
                ([gene_metadata.get(t['geneId'], MAX_SORT_RANK)for t in x[TRANSCRIPT_CONSEQUENCES_FIELD] if t['geneId'] in gene_metadata]
                if x.get(TRANSCRIPT_CONSEQUENCES_FIELD) else [gene_metadata.get(gene_id, MAX_SORT_RANK) for gene_id in x.get('transcripts', {}).keys()])
                or [MAX_SORT_RANK]
            ),
        ]

    return lambda x: tuple(expr(x[0] if isinstance(x, list) else x) for expr in [*sort_expressions, lambda x: x[XPOS_SORT_KEY]])


def _clickhouse_variant_lookup(variant_id, genome_version, data_type, samples):
    entry_cls = ENTRY_CLASS_MAP[genome_version][data_type]
    annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][data_type]

    sample_data = _get_sample_data(samples)[data_type] if samples else None

    if isinstance(variant_id, str):
        # Since there is no efficient way to prefilter SV entries based on the variant id, explicitly look up the keys
        keys = KEY_LOOKUP_CLASS_MAP[genome_version][data_type].objects.filter(variant_id=variant_id).values_list('key', flat=True)
        entries = entry_cls.objects.filter(key__in=keys)
    else:
        entries = entry_cls.objects.filter_locus(variant_ids=[variant_id])

    entries = entries.result_values(sample_data)
    results = annotations_cls.objects.subquery_join(entries)
    if isinstance(variant_id, str):
        # Handles annotation for genotype overrides
        results = results.filter_annotations(results)
    else:
        results = results.filter_variant_ids(variant_ids=[variant_id])

    variant = results.result_values().first()
    if variant:
        variant = format_clickhouse_results([variant], genome_version)[0]
    return variant

def clickhouse_variant_lookup(user, variant_id, data_type, genome_version=None, samples=None, **kwargs):
    logger.info(f'Looking up variant {variant_id} with data type {data_type}', user)

    variant = _clickhouse_variant_lookup(variant_id, genome_version, data_type, samples)
    if variant:
        _add_liftover_genotypes(variant, data_type, variant_id)
    else:
        lifted_genome_version = next(gv for gv in ENTRY_CLASS_MAP.keys() if gv != genome_version)
        if ENTRY_CLASS_MAP[lifted_genome_version].get(data_type):
            from seqr.utils.search.utils import run_liftover
            liftover_results = run_liftover(lifted_genome_version, variant_id[0], variant_id[1])
            if liftover_results:
                lifted_id = (liftover_results[0], liftover_results[1], *variant_id[2:])
                variant = _clickhouse_variant_lookup(lifted_id, lifted_genome_version, data_type, samples)

    if not variant:
        raise ObjectDoesNotExist('Variant not present in seqr')

    return variant


def _add_liftover_genotypes(variant, data_type, variant_id):
    lifted_entry_cls = ENTRY_CLASS_MAP.get(variant.get('liftedOverGenomeVersion'), {}).get(data_type)
    if not lifted_entry_cls:
        return
    lifted_id = (variant['liftedOverChrom'], variant['liftedOverPos'], *variant_id[2:])
    keys = KEY_LOOKUP_CLASS_MAP[variant['liftedOverGenomeVersion']][data_type].objects.filter(
        variant_id='-'.join([str(o) for o in lifted_id]),
    ).values_list('key', flat=True)
    if not keys:
        return
    lifted_entries = lifted_entry_cls.objects.filter_locus(variant_ids=[lifted_id]).filter(key=keys[0])
    lifted_entry_data = lifted_entries.values('key').annotate(
        familyGenotypes=GroupArrayArray(lifted_entry_cls.objects.genotype_expression())
    )
    if lifted_entry_data:
        variant['familyGenotypes'].update(lifted_entry_data[0]['familyGenotypes'])
        variant['liftedFamilyGuids'] = sorted(lifted_entry_data[0]['familyGenotypes'].keys())


def get_clickhouse_variant_by_id(variant_id, samples, genome_version, dataset_type):
    if dataset_type == Sample.DATASET_TYPE_SV_CALLS:
        data_types  = [
            f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}'
            for sample_type in samples.values_list('sample_type', flat=True).distinct()
        ]
    else:
        data_types = [dataset_type]
    for data_type in data_types:
        variant = _clickhouse_variant_lookup(variant_id, genome_version, data_type, samples)
        if variant:
            return variant
    return None


def get_clickhouse_genotypes(project_guid, family_guids, genome_version, dataset_type, keys, samples):
    sample_data = _get_sample_data(samples.filter(individual__family__guid__in=family_guids))[dataset_type]
    entries = ENTRY_CLASS_MAP[genome_version][dataset_type].objects.filter(
        project_guid=project_guid, family_guid__in=family_guids, key__in=keys,
    )
    return {
        key: json.loads(json.dumps(genotypes, cls=DjangoJSONEncoderWithSets)) for key, genotypes in
        entries.annotate(genotypes=entries.genotype_expression(sample_data)).values_list('key', 'genotypes')
    }


def get_annotations_queryset(genome_version, dataset_type, keys):
    annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][dataset_type]
    return annotations_cls.objects.filter(key__in=keys)


def get_clickhouse_annotations(genome_version, dataset_type, keys):
    qs = get_annotations_queryset(genome_version, dataset_type, keys)
    results = qs.join_seqr_pop().join_clinvar(keys).result_values(skip_entry_fields=True)
    return format_clickhouse_results(results, genome_version)


def get_clickhouse_genes(genome_version, dataset_type, keys):
    results = get_annotations_queryset(genome_version, dataset_type, keys)
    return results.aggregate(
        gene_ids=ArrayDistinct(GroupArrayArray(ArrayMap(results.transcript_field, mapped_expression='x.geneId')), output_field=ArrayField(StringField())),
    )['gene_ids']


def get_clickhouse_keys_for_gene(gene_id, genome_version, dataset_type, keys):
    results = get_annotations_queryset(genome_version, dataset_type, keys)
    return list(results.filter(
        **{f'{results.transcript_field}__array_exists': {'geneId': (f"'{gene_id}'",)}},
    ).values_list('key', flat=True))


def get_all_clickhouse_keys_for_gene(gene_model, genome_version):
    entry_cls = ENTRY_CLASS_MAP[genome_version][Sample.DATASET_TYPE_VARIANT_CALLS]
    return list(entry_cls.objects.filter_locus(require_gene_filter=True, gene_intervals={
        gene_model.id: [getattr(gene_model, f'{field}_grch{genome_version}') for field in ['chrom', 'start', 'end']]
    }).values_list('key', flat=True).distinct())


def get_clickhouse_key_lookup(genome_version, dataset_type, variants_ids, reverse=False):
    key_lookup_class = KEY_LOOKUP_CLASS_MAP[genome_version][dataset_type]
    lookup = {}
    fields = ('variant_id', 'key') if not reverse else ('key', 'variant_id')
    for i in range(0, len(variants_ids), BATCH_SIZE):
        batch = variants_ids[i:i + BATCH_SIZE]
        lookup.update(dict(key_lookup_class.objects.filter(variant_id__in=batch).values_list(*fields)))
    return lookup


def delete_clickhouse_project(project, dataset_type, sample_type=None):
    dataset_type = _clickhouse_dataset_type(dataset_type, sample_type)
    table_base = f'{GENOME_VERSION_LOOKUP[project.genome_version]}/{dataset_type}'
    with connections['clickhouse_write'].cursor() as cursor:
        cursor.execute(f'ALTER TABLE "{table_base}/entries" DROP PARTITION %s', [project.guid])
        if dataset_type != 'GCNV':
            cursor.execute(f'ALTER TABLE "{table_base}/project_gt_stats" DROP PARTITION %s', [project.guid])
            view_name = f'{table_base}/project_gt_stats_to_gt_stats_mv'
            cursor.execute(f'SYSTEM REFRESH VIEW "{view_name}"')
            cursor.execute(f'SYSTEM WAIT VIEW "{view_name}"')
            cursor.execute(f'SYSTEM RELOAD DICTIONARY "{table_base}/gt_stats_dict"')
    return f'Deleted all {dataset_type} search data for project {project.name}'


def delete_clickhouse_family(project, family_guid, dataset_type, sample_type=None):
    dataset_type = _clickhouse_dataset_type(dataset_type, sample_type)
    return f'Clickhouse does not support deleting individual families from project. Manually delete {dataset_type} data for {family_guid} in project {project.guid}'


def _clickhouse_dataset_type(dataset_type, sample_type):
    if dataset_type == Sample.DATASET_TYPE_SV_CALLS:
        if not sample_type:
            raise ValueError('sample_type is required when dataset_type is SV')
        if sample_type == Sample.SAMPLE_TYPE_WES:
            return 'GCNV'
    return dataset_type