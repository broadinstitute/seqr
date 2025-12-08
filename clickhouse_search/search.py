from clickhouse_backend.models import ArrayField, StringField
from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections
from django.db.models import Count, F, Min, Q
from django.db.models.functions import JSONObject
import json

from clickhouse_search.backend.fields import NamedTupleField
from clickhouse_search.backend.functions import Array, ArrayFilter, ArrayIntersect, ArraySort, GroupArrayArray, If, Tuple, \
    ArrayMap
from clickhouse_search.models import ENTRY_CLASS_MAP, ANNOTATIONS_CLASS_MAP, TRANSCRIPTS_CLASS_MAP, KEY_LOOKUP_CLASS_MAP, \
    BaseClinvar, BaseAnnotationsMitoSnvIndel, BaseAnnotationsGRCh37SnvIndel, BaseAnnotationsSvGcnv
from reference_data.models import GeneConstraint, Omim, GENOME_VERSION_LOOKUP
from seqr.models import Sample, PhenotypePrioritization, Individual
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.search.constants import MAX_VARIANTS, XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY, \
    PRIORITIZED_GENE_SORT, COMPOUND_HET, COMPOUND_HET_ALLOW_HOM_ALTS, RECESSIVE, AFFECTED, MALE_SEXES, \
    X_LINKED_RECESSIVE, X_LINKED_RECESSIVE_MALE_AFFECTED
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets

logger = SeqrLogger(__name__)

BATCH_SIZE = 10000

TRANSCRIPT_CONSEQUENCES_FIELD = 'sortedTranscriptConsequences'
SELECTED_GENE_FIELD = 'selectedGeneId'
SELECTED_TRANSCRIPT_FIELD = 'selectedTranscript'


def get_clickhouse_variants(samples, search, user, previous_search_results, genome_version,page=1, num_results=100, sort=None, **kwargs):
    inheritance_mode = search.get('inheritance_mode')
    has_comp_het = inheritance_mode in {RECESSIVE, COMPOUND_HET}
    has_x_chrom_comp_het = has_comp_het and _is_x_chrom_only(genome_version, **search)
    has_x_linked = inheritance_mode in {RECESSIVE, X_LINKED_RECESSIVE} and _has_x_chrom(genome_version, **search)
    sample_data_by_dataset_type = _get_sample_data(
        samples,
        skip_multi_project_individual_guid=True,
        annotate_affected_males=has_x_chrom_comp_het or has_x_linked,
    )
    results = []
    family_guid = None
    exclude_keys = search.pop('exclude_keys', None) or {}
    exclude_key_pairs = search.pop('exclude_key_pairs', None) or {}
    search.pop('dataset_type', None)
    for dataset_type, sample_data in sample_data_by_dataset_type.items():
        logger.info(f'Loading {dataset_type} data for {sample_data["num_families"]} families', user)

        family_guid = next(iter(next(iter(sample_data['sample_type_families'].values()))))

        dataset_results = []
        if inheritance_mode != COMPOUND_HET:
            dataset_results += _get_search_results(genome_version, dataset_type, sample_data, exclude_keys=exclude_keys.get(dataset_type), **search)

        run_x_linked_male_search = has_x_linked and not (inheritance_mode == X_LINKED_RECESSIVE and sample_data.get('samples'))
        if run_x_linked_male_search:
            affected_male_family_guids = {
                s['family_guid'] for s in sample_data['samples'] if s['affected'] == AFFECTED and s['sex'] in MALE_SEXES
            } if 'samples' in sample_data else sample_data['affected_male_family_guids']
            if affected_male_family_guids:
                x_linked_sample_data = _affected_male_families(sample_data, affected_male_family_guids)
                x_linked_search = {**search, 'inheritance_mode': X_LINKED_RECESSIVE_MALE_AFFECTED}
                logger.info(f'Loading {dataset_type} X-linked male data for {x_linked_sample_data["num_families"]} families', user)
                dataset_results += _get_search_results(
                    genome_version, dataset_type, x_linked_sample_data, exclude_keys=exclude_keys.get(dataset_type),
                    **x_linked_search,
                )

        if has_comp_het:
            comp_het_sample_data = sample_data
            if has_x_chrom_comp_het and 'affected_male_family_guids' in sample_data and dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
                comp_het_sample_data = _no_affected_male_families(sample_data, user)
            result_q = get_data_type_comp_het_results_queryset(genome_version, dataset_type, comp_het_sample_data, exclude_key_pairs=exclude_key_pairs.get(dataset_type), **search)
            dataset_results += _evaluate_results(result_q, is_comp_het=True)

        if 'samples' not in sample_data:
            add_individual_guids(dataset_results, samples)
        results += dataset_results

    if has_comp_het and Sample.DATASET_TYPE_VARIANT_CALLS in sample_data_by_dataset_type and any(
        dataset_type.startswith(Sample.DATASET_TYPE_SV_CALLS) for dataset_type in sample_data_by_dataset_type
    ):
        results += _get_multi_data_type_comp_het_results(genome_version, samples, sample_data_by_dataset_type, user, exclude_key_pairs, **search)

    cache_results = get_clickhouse_cache_results(results, sort, family_guid)
    previous_search_results.update(cache_results)

    logger.info(f'Total results: {cache_results["total_results"]}', user)

    return format_clickhouse_results(cache_results['all_results'][(page-1)*num_results:page*num_results], genome_version)

def get_search_queryset(genome_version, dataset_type, sample_data, **search_kwargs):
    entry_cls = ENTRY_CLASS_MAP[genome_version][dataset_type]
    annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][dataset_type]
    entries = entry_cls.objects.search(sample_data, **search_kwargs)
    return annotations_cls.objects.subquery_join(entries).search(**search_kwargs)


def _get_search_results(*args, skip_entry_fields=False, order_by=None, **search_kwargs):
    results = get_search_queryset(*args, skip_entry_fields=skip_entry_fields, **search_kwargs)
    if order_by:
        results = results.order_by(order_by)
    return _evaluate_results(results.result_values(skip_entry_fields=skip_entry_fields))


def _evaluate_results(result_q, is_comp_het=False):
    results = [list(result[1:]) if is_comp_het else result for result in result_q[:MAX_VARIANTS + 1]]
    if len(results) > MAX_VARIANTS:
        from seqr.utils.search.utils import InvalidSearchException
        raise InvalidSearchException('This search returned too many results')
    return results

def _get_multi_data_type_comp_het_results(genome_version, samples, sample_data_by_dataset_type, user, exclude_key_pairs, annotations=None, annotations_secondary=None, inheritance_mode=None, **search_kwargs):
    if annotations_secondary:
        annotations = {
            **annotations,
            **{k: v + annotations[k] if k in annotations else v for k, v in annotations_secondary.items()},
        }

    snv_indel_sample_data = sample_data_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS]
    snv_indel_families = set().union(*snv_indel_sample_data['sample_type_families'].values())

    results = []
    for sample_type in [Sample.SAMPLE_TYPE_WES, Sample.SAMPLE_TYPE_WGS]:
        sv_dataset_type = f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}'
        sv_sample_data = sample_data_by_dataset_type.get(sv_dataset_type, {})
        sv_families = set(sv_sample_data.get('sample_type_families', {}).get(sample_type, []))
        families = snv_indel_families.intersection(sv_families)
        if not families:
            continue
        logger.info(f'Loading {Sample.DATASET_TYPE_VARIANT_CALLS}/{sv_dataset_type} data for {len(families)} families', user)

        snv_indel_sample_type_families = {
            sample_type: familes.intersection(sv_families)
            for sample_type, familes in snv_indel_sample_data['sample_type_families'].items()
        }
        snv_indel_sample_type_families = {k: v for k, v in snv_indel_sample_type_families.items() if v}
        type_snv_indel_sample_data = {
            **snv_indel_sample_data,
            'num_families': len(families),
            'sample_type_families': snv_indel_sample_type_families,
            'samples': [s for s in snv_indel_sample_data['samples'] if s['family_guid'] in families] if 'samples' in snv_indel_sample_data else None,
        }

        sv_sample_data = {
            **sv_sample_data,
            'num_families': len(families),
            'sample_type_families': {sample_type: families},
            'samples': [s for s in sv_sample_data['samples'] if s['family_guid'] in families] if 'samples' in sv_sample_data else None,
        }

        result_q = get_multi_data_type_comp_het_results_queryset(
            genome_version, sv_dataset_type, sv_sample_data, type_snv_indel_sample_data, num_families=len(families),
            exclude_key_pairs=exclude_key_pairs.get(f'{Sample.DATASET_TYPE_VARIANT_CALLS},{sv_dataset_type}'),
            annotations=annotations, **search_kwargs,
        )
        dataset_results = _evaluate_results(result_q, is_comp_het=True)
        if not sv_sample_data['samples']:
            add_individual_guids(dataset_results, samples)
        results += dataset_results

    return results


def get_multi_data_type_comp_het_results_queryset(genome_version, sv_dataset_type, sv_sample_data, snv_indel_sample_data, num_families, exclude_key_pairs=None, **kwargs):
    entries = ENTRY_CLASS_MAP[genome_version][Sample.DATASET_TYPE_VARIANT_CALLS].objects.search(
        snv_indel_sample_data, inheritance_mode=COMPOUND_HET_ALLOW_HOM_ALTS, annotate_carriers=True,
        annotate_hom_alts=True, **kwargs,
    )
    annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][Sample.DATASET_TYPE_VARIANT_CALLS]
    snv_indel_q = annotations_cls.objects.subquery_join(entries).search(**kwargs)

    sv_entries = ENTRY_CLASS_MAP[genome_version][sv_dataset_type].objects.search(
        sv_sample_data, **kwargs, inheritance_mode=COMPOUND_HET, annotate_carriers=True,
    )
    sv_annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][sv_dataset_type]
    sv_q = sv_annotations_cls.objects.subquery_join(sv_entries).search(**kwargs)

    return _get_comp_het_results_queryset(annotations_cls, snv_indel_q, sv_q, num_families, exclude_key_pairs)


def get_data_type_comp_het_results_queryset(genome_version, dataset_type, sample_data, annotations=None, annotations_secondary=None, pathogenicity=None, inheritance_mode=None, exclude_key_pairs=None, split_pathogenicity_annotations=False, **search_kwargs):
    entry_cls = ENTRY_CLASS_MAP[genome_version][dataset_type]
    annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][dataset_type]
    entries = entry_cls.objects.search(
        sample_data, **search_kwargs, inheritance_mode=COMPOUND_HET, pathogenicity=pathogenicity, annotations=annotations, annotate_carriers=True,
    )

    if split_pathogenicity_annotations:
        pathogenicity_secondary = pathogenicity
        pathogenicity = None
    else:
        annotations_secondary = annotations_secondary or annotations
        pathogenicity_secondary = pathogenicity
    primary_q = annotations_cls.objects.subquery_join(entries).search(
        annotations=annotations, pathogenicity=pathogenicity, **search_kwargs,
    )
    secondary_q = annotations_cls.objects.subquery_join(entries).search(
        annotations=annotations_secondary, pathogenicity=pathogenicity_secondary, **search_kwargs,
    )

    return _get_comp_het_results_queryset(annotations_cls, primary_q, secondary_q, sample_data['num_families'], exclude_key_pairs)


def _get_comp_het_results_queryset(annotations_cls, primary_q, secondary_q, num_families, exclude_key_pairs):
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

    pair_results = results.annotate(
        pair_key=ArraySort(Array('primary_key', 'secondary_key')),
    ).distinct('pair_key')
    if exclude_key_pairs:
        pair_results = pair_results.exclude(pair_key__in=exclude_key_pairs)
    return pair_results.values_list(
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


def add_individual_guids(results, samples, encode_genotypes_json=False):
    families = set()
    for result in results:
        for r in (result if isinstance(result, list) else [result]):
            families.update(r.get('familyGenotypes', {}).keys())
    sample_map = {
        (family_guid, sample_id): individual_guid for family_guid, individual_guid, sample_id in samples.filter(
            individual__family__guid__in=families,
        ).values_list('individual__family__guid', 'individual__guid', 'sample_id')
    }
    for result in results:
        if isinstance(result, list):
            for variant in result:
                _set_individual_guids(variant, sample_map, encode_genotypes_json)
        else:
            _set_individual_guids(result, sample_map, encode_genotypes_json)


def _set_individual_guids(result, sample_map, encode_genotypes_json):
    if 'familyGenotypes' not in result:
        return
    result['familyGuids'] = sorted(result['familyGenotypes'].keys())
    individual_genotypes =  defaultdict(list)
    for family_guid, genotypes in result.pop('familyGenotypes').items():
        for genotype in genotypes:
            individual_guid = sample_map[(family_guid, genotype['sampleId'])]
            individual_genotypes[individual_guid].append({**genotype, 'individualGuid': individual_guid})
    genotypes = {k: v[0] if len(v) == 1 else v for k, v in individual_genotypes.items()}
    if encode_genotypes_json:
        genotypes = _clickhouse_genotypes_json(genotypes)
    result['genotypes'] = genotypes


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


def _get_sample_data(samples, skip_multi_project_individual_guid=False, annotate_affected_males=False):
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

    skip_individual_guid = (
        skip_multi_project_individual_guid and samples.values('individual__family__project_id').distinct().count() > 1
    )
    annotations = {
        'project_guids': ArrayAgg('individual__family__project__guid', distinct=True),
        'family_guids': ArrayAgg('individual__family__guid', distinct=True),
    }
    if skip_individual_guid:
        annotations['num_unaffected'] = Count(
            'individual_id', distinct=True, filter=Q(individual__affected=Individual.AFFECTED_STATUS_UNAFFECTED),
        )
        if annotate_affected_males:
            annotations['affected_male_family_guids'] = ArrayAgg('individual__family__guid', distinct=True, filter=Q(
                individual__affected=Individual.AFFECTED_STATUS_AFFECTED, individual__sex__in=Individual.MALE_SEXES,
            ))
    else:
        annotations['samples'] = ArrayAgg(JSONObject(
            affected='individual__affected', sex='individual__sex', sample_id='sample_id', sample_type='sample_type', family_guid=F('individual__family__guid'), individual_guid=F('individual__guid'),
        ))

    sample_data = samples.values('dataset_type', 'sample_type').annotate(**annotations)
    samples_by_dataset_type = {}
    for data in sample_data:
        dataset_type = data.pop('dataset_type')
        sample_type = data.pop('sample_type')
        if dataset_type == Sample.DATASET_TYPE_SV_CALLS:
            dataset_type = f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}'

        family_guids = set(data.pop('family_guids'))
        if dataset_type in samples_by_dataset_type:
            other_type_data = samples_by_dataset_type[dataset_type]
            other_sample_type, other_type_family_guids = next(iter(other_type_data['sample_type_families'].items()))
            sample_type_families = {
                other_sample_type: other_type_family_guids - family_guids,
                sample_type: family_guids - other_type_family_guids,
                'multi': family_guids.intersection(other_type_family_guids),
            }
            if sample_type_families['multi']:
                data['family_missing_type_samples'] = defaultdict(lambda: defaultdict(list))
                individual_samples = {s['individual_guid']: s for s in data.get('samples', [])}
                other_type_individual_samples = {s['individual_guid']: s for s in other_type_data.get('samples', [])}
                for individual_guid in set(individual_samples.keys()) - set(other_type_individual_samples.keys()):
                    sample = individual_samples[individual_guid]
                    data['family_missing_type_samples'][sample['family_guid']][other_sample_type].append(sample['sample_id'])
                for individual_guid in set(other_type_individual_samples.keys()) -  set(individual_samples.keys()):
                    sample = other_type_individual_samples[individual_guid]
                    data['family_missing_type_samples'][sample['family_guid']][sample_type].append(sample['sample_id'])
            data['sample_type_families'] = {k: v for k, v in sample_type_families.items() if v}
            for key in ['project_guids', 'samples']:
                if key in data:
                    data[key] += other_type_data[key]
        else:
            data['sample_type_families'] = {sample_type: family_guids}

        samples_by_dataset_type[dataset_type] = {
            **data,
            'num_families': len(set().union(*data['sample_type_families'].values())),
        }

    _add_missing_multi_type_samples(samples, samples_by_dataset_type)

    return samples_by_dataset_type


def _add_missing_multi_type_samples(samples, samples_by_dataset_type):
    for dataset_type, data in samples_by_dataset_type.items():
        if data['sample_type_families'].get('multi') and 'samples' not in data:
            individual_samples = samples.filter(
                dataset_type=dataset_type, individual__family__guid__in=data['sample_type_families']['multi'],
            ).values('individual_id', family_guid=F('individual__family__guid')).annotate(
                samples=ArrayAgg(JSONObject(sample_id='sample_id', sample_type='sample_type'))
            ).filter(samples__len=1)
            for agg in individual_samples:
                sample = agg['samples'][0]
                missing_type = Sample.SAMPLE_TYPE_WES if sample['sample_type'] == Sample.SAMPLE_TYPE_WGS else Sample.SAMPLE_TYPE_WGS
                data['family_missing_type_samples'][agg['family_guid']][missing_type].append(sample['sample_id'])


def _no_affected_male_families(sample_data, user):
    sample_type_families = {
        sample_type: families - set(sample_data['affected_male_family_guids'])
        for sample_type, families in sample_data['sample_type_families'].items()
    }
    num_families = len(set().union(*sample_type_families.values()))
    logger.info(f'Loading X-chromosome compound het data for {num_families} families', user)
    return {
        **sample_data,
        'num_families': num_families,
        'sample_type_families': {sample_type: families for sample_type, families in sample_type_families.items() if families},
    }


def _affected_male_families(sample_data, affected_male_family_guids):
    if len(affected_male_family_guids) == sample_data['num_families']:
        return sample_data
    sample_type_families = {
        sample_type: families.intersection(affected_male_family_guids)
        for sample_type, families in sample_data['sample_type_families'].items()
    }
    return {
        **sample_data,
        'num_families': len(set().union(*sample_type_families.values())),
        'sample_type_families': {sample_type: families for sample_type, families in sample_type_families.items() if families},
    }


def _is_x_chrom_only(genome_version, genes=None, intervals=None, **kwargs):
    if not (genes or intervals):
        return False
    return all('X' in gene[f'chromGrch{genome_version}'] for gene in (genes or {}).values()) and all('X' in interval['chrom'] for interval in (intervals or []))


def _has_x_chrom(genome_version, genes=None, intervals=None, **kwargs):
    if not (genes or intervals):
        return True
    return any('X' in gene[f'chromGrch{genome_version}'] for gene in (genes or {}).values()) or any('X' in interval['chrom'] for interval in (intervals or []))


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


def clickhouse_variant_gene_lookup(user, gene, genome_version, search):
    logger.info(f'Looking up variants in gene {gene["geneId"]}', user)
    results = _get_search_results(
        genome_version, Sample.DATASET_TYPE_VARIANT_CALLS, sample_data=None, genes={gene['geneId']: gene}, skip_entry_fields=True, order_by='xpos', **search,
    )
    return format_clickhouse_results(results, genome_version)


def _clickhouse_variant_lookup(variant_id, genome_version, data_type, samples=None, affected_only=False, hom_only=False):
    entry_cls = ENTRY_CLASS_MAP[genome_version][data_type]
    annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][data_type]

    sample_data = _get_sample_data(samples)[data_type] if samples else None

    if isinstance(variant_id, str):
        # Since there is no efficient way to prefilter SV entries based on the variant id, explicitly look up the keys
        keys = KEY_LOOKUP_CLASS_MAP[genome_version][data_type].objects.filter(variant_id=variant_id).values_list('key', flat=True)
        entries = entry_cls.objects.filter(key__in=keys)
    else:
        entries = entry_cls.objects.filter_locus(parsed_variant_ids=[variant_id])

    entries = _filter_lookup_entries(entries, affected_only, hom_only)
    entries = entries.result_values(sample_data)
    results = annotations_cls.objects.subquery_join(entries)
    if isinstance(variant_id, str):
        # Handles annotation for genotype overrides
        results = results.filter_annotations(results)
    else:
        results = results.filter_variant_ids(parsed_variant_ids=[variant_id])

    variant = results.result_values().first()
    if variant:
        variant = format_clickhouse_results([variant], genome_version)[0]
    return variant

def _filter_lookup_entries(entries, affected_only, hom_only):
    if affected_only:
        entries = entries.filter(entries.any_affected_q())
    if hom_only:
        entries = entries.filter(calls__array_exists={'gt': (2,)})
    return entries

def clickhouse_variant_lookup(user, variant_id, dataset_type, sample_type, genome_version, affected_only, hom_only):
    is_sv = dataset_type == Sample.DATASET_TYPE_SV_CALLS
    data_type = f'{dataset_type}_{sample_type}' if is_sv else dataset_type
    logger.info(f'Looking up variant {variant_id} with data type {data_type}', user)

    variant = _clickhouse_variant_lookup(
        variant_id, genome_version, data_type, affected_only=affected_only, hom_only=hom_only,
    )
    if variant:
        _add_liftover_genotypes(variant, data_type, variant_id, affected_only, hom_only)
    else:
        lifted_genome_version = next(gv for gv in ENTRY_CLASS_MAP.keys() if gv != genome_version)
        if ENTRY_CLASS_MAP[lifted_genome_version].get(data_type):
            from seqr.utils.search.utils import run_liftover
            liftover_results = run_liftover(lifted_genome_version, variant_id[0], variant_id[1])
            if liftover_results:
                lifted_id = (liftover_results[0], liftover_results[1], *variant_id[2:])
                variant = _clickhouse_variant_lookup(
                    lifted_id, lifted_genome_version, data_type, affected_only=affected_only, hom_only=hom_only,
                )

    if not variant:
        raise ObjectDoesNotExist('Variant not present in seqr')

    variants = [variant]

    if is_sv and variant['svType'] in {'DEL', 'DUP'}:
        other_sample_type, other_entry_class = next(
            (dt, cls) for dt, cls in ENTRY_CLASS_MAP[genome_version].items()
            if dt != data_type and dt.startswith(Sample.DATASET_TYPE_SV_CALLS)
        )
        other_annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][other_sample_type]

        padding = int((variant['end'] - variant['pos']) * 0.2)
        entries = other_entry_class.objects.search_padded_interval(variant['chrom'], variant['pos'], padding)
        entries = _filter_lookup_entries(entries, affected_only, hom_only)
        results = other_annotations_cls.objects.subquery_join(entries).search(
            padded_interval_end=(variant['end'], padding),
            annotations={'structural': [variant['svType'], f"gCNV_{variant['svType']}"]},
        )
        variants += list(results.result_values())

    return variants


def _add_liftover_genotypes(variant, data_type, variant_id, affected_only, hom_only):
    lifted_entry_cls = ENTRY_CLASS_MAP.get(variant.get('liftedOverGenomeVersion'), {}).get(data_type)
    if not lifted_entry_cls:
        return
    lifted_id = (variant['liftedOverChrom'], variant['liftedOverPos'], *variant_id[2:])
    keys = KEY_LOOKUP_CLASS_MAP[variant['liftedOverGenomeVersion']][data_type].objects.filter(
        variant_id='-'.join([str(o) for o in lifted_id]),
    ).values_list('key', flat=True)
    if not keys:
        return
    lifted_entries = lifted_entry_cls.objects.filter_locus(parsed_variant_ids=[lifted_id]).filter(key=keys[0])
    lifted_entries = _filter_lookup_entries(lifted_entries, affected_only, hom_only)
    gt_field, gt_expr = lifted_entry_cls.objects.genotype_expression()
    lifted_entry_data = lifted_entries.values('key').annotate(**{gt_field: GroupArrayArray(gt_expr)})
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
    gt_field, gt_expr = entries.genotype_expression(sample_data)
    return {
        key: _clickhouse_genotypes_json(genotypes) for key, genotypes in
        entries.annotate(**{gt_field: gt_expr}).values_list('key', 'genotypes')
    }


def _clickhouse_genotypes_json(genotypes):
    return json.loads(json.dumps(genotypes, cls=DjangoJSONEncoderWithSets))


def get_annotations_queryset(genome_version, dataset_type, keys):
    annotations_cls = ANNOTATIONS_CLASS_MAP[genome_version][dataset_type]
    return annotations_cls.objects.filter(key__in=keys)


def get_clickhouse_annotations(genome_version, dataset_type, keys):
    qs = get_annotations_queryset(genome_version, dataset_type, keys)
    results = qs.join_seqr_pop().join_clinvar(keys).result_values(skip_entry_fields=True)
    return format_clickhouse_results(results, genome_version)


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


def reload_clickhouse_sex_dict():
    with connections['clickhouse_write'].cursor() as cursor:
        cursor.execute('SYSTEM RELOAD DICTIONARY "seqrdb_sex_dict"')


SV_DATASET_TYPES = {
    Sample.SAMPLE_TYPE_WGS: Sample.DATASET_TYPE_SV_CALLS,
    Sample.SAMPLE_TYPE_WES: 'GCNV',
}
def _clickhouse_dataset_type(dataset_type, sample_type):
    if dataset_type == Sample.DATASET_TYPE_SV_CALLS:
        dataset_type = SV_DATASET_TYPES[sample_type]
    return dataset_type