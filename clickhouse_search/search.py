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
    ArrayMap, Modulo
from clickhouse_search.managers import InvalidDatasetTypeException, InvalidSearchException
from clickhouse_search.models.gt_stats_models import PROJECT_GT_STATS_VIEW_CLASS_MAP
from clickhouse_search.models.reference_data_models import BaseClinvar, BaseHgmd
from clickhouse_search.models.search_models import BaseVariants, BaseVariantsSvGcnv, \
    ENTRY_CLASS_MAP, VARIANTS_CLASS_MAP, VARIANT_DETAILS_CLASS_MAP
from reference_data.models import GeneInfo, GeneConstraint, Omim, GENOME_VERSION_LOOKUP
from seqr.models import Sample, PhenotypePrioritization, Family, Individual
from seqr.utils.gene_utils import parse_locus_list_items
from seqr.utils.logging_utils import SeqrLogger
from clickhouse_search.constants import MAX_VARIANTS, XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY, \
    PRIORITIZED_GENE_SORT, COMPOUND_HET, COMPOUND_HET_ALLOW_HOM_ALTS, RECESSIVE, AFFECTED, MALE_SEXES, \
    X_LINKED_RECESSIVE, X_LINKED_RECESSIVE_MALE_AFFECTED
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets

logger = SeqrLogger(__name__)


BATCH_SIZE = 10000
MAX_GENES_FOR_FILTER = 10000
MAX_NO_LOCATION_COMP_HET_FAMILIES = 100
MIN_MULTI_FAMILY_SEQR_AC = 5000

TRANSCRIPT_CONSEQUENCES_FIELD = 'sortedTranscriptConsequences'
SELECTED_GENE_FIELD = 'selectedGeneId'
SELECTED_TRANSCRIPT_FIELD = 'selectedTranscript'


def get_clickhouse_variants(families, user, genome_version=None, sort=None, sample_data_by_dataset_type=None, encode_genotypes_json=False, inheritance=None, locus=None, exclude_keys=None, exclude_key_pairs=None, no_access_project_genome_version=None, **search):
    genome_version = genome_version or no_access_project_genome_version or _get_search_genome_version(families)

    search['inheritance_filter'] = (inheritance or {}).get('filter') or {}
    inheritance_mode = None if search['inheritance_filter'].get('genotype') else (inheritance or {}).get('mode')
    _parse_locus_search(locus or {}, genome_version, search)

    has_comp_het = inheritance_mode in {RECESSIVE, COMPOUND_HET}
    has_x_chrom_comp_het = has_comp_het and _is_x_chrom_only(**search)
    has_x_linked = inheritance_mode in {RECESSIVE, X_LINKED_RECESSIVE} and _has_x_chrom(**search)
    sample_data_by_dataset_type = sample_data_by_dataset_type or {}
    results = []
    searched_dataset_types = set()
    sample_data_errors = set()
    for dataset_type in ENTRY_CLASS_MAP[genome_version]:
        try:
            entry_qs, variants_qs, parsed_filters = _parse_dataset_type_query(
                genome_version, dataset_type, families, sample_data_by_dataset_type, sample_data_errors,
                annotate_affected_males=has_x_chrom_comp_het or has_x_linked,
                allow_no_samples=bool(no_access_project_genome_version), inheritance_mode=inheritance_mode, **search,
            )
        except InvalidDatasetTypeException:
            continue

        if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS and no_access_project_genome_version:
            results += _get_no_access_search_results(
                entry_qs, variants_qs, has_comp_het, user, **search, **parsed_filters,
                exclude_projects=sample_data_by_dataset_type[dataset_type].get('project_guids'), inheritance_mode=inheritance_mode,
            )
            searched_dataset_types.add(dataset_type)

        sample_data = sample_data_by_dataset_type[dataset_type]
        if not sample_data:
            continue

        logger.info(f'Loading {dataset_type} data for {sample_data["num_families"]} families', user)

        dataset_results = []
        if inheritance_mode != COMPOUND_HET:
            dataset_results += _get_search_results(
                entry_qs, variants_qs, sample_data, inheritance_mode=inheritance_mode, exclude_keys=(exclude_keys or {}).get(dataset_type), **search, **parsed_filters,
            )

        run_x_linked_male_search = has_x_linked and not (inheritance_mode == X_LINKED_RECESSIVE and sample_data.get('samples'))
        if run_x_linked_male_search:
            dataset_results += _get_x_linked_male_search_results(
                entry_qs, variants_qs, dataset_type, user, sample_data, exclude_keys=(exclude_keys or {}).get(dataset_type),
                **search, **parsed_filters,
            )

        if has_comp_het:
            dataset_results += _get_data_type_comp_het_results_queryset(
                entry_qs, variants_qs, sample_data, user, parsed_filters, **search,
                exclude_key_pairs=(exclude_key_pairs or {}).get(dataset_type),
                is_x_chrom=has_x_chrom_comp_het and dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS,
            )

        if 'samples' not in sample_data:
            _add_individual_guids(dataset_results, encode_genotypes_json=encode_genotypes_json)
        results += dataset_results
        searched_dataset_types.add(dataset_type)

    if has_comp_het and any(dt.startswith(Sample.DATASET_TYPE_SV_CALLS) for dt in VARIANTS_CLASS_MAP[genome_version]):
        results += _get_multi_data_type_comp_het_results(genome_version, families, sample_data_by_dataset_type, user, exclude_key_pairs or {}, searched_dataset_types, **search)

    if not searched_dataset_types:
        _raise_dataset_type_errors(sample_data_errors, sample_data_by_dataset_type)

    logger.info(f'Total results: {len(results)}', user)
    return get_sorted_search_results(results, sort, families)


def  _get_search_genome_version(families):
    genome_versions = families.values_list('project__genome_version', flat=True).distinct()
    if len (genome_versions) > 1:
        project_versions = families.values('project__genome_version').annotate(
            projects=ArrayAgg('project__name', distinct=True)
        )
        summary = '; '.join(
            sorted([f"{agg['project__genome_version']} - {', '.join(sorted(agg['projects']))}" for agg in project_versions]))
        raise InvalidSearchException(
            f'Searching across multiple genome builds is not supported. Remove projects with differing genome builds from search: {summary}')

    return genome_versions[0]


def _parse_locus_search(locus, genome_version, search):
    exclude = search.get('exclude') or {}
    exclude_locations = bool(exclude.get('rawItems'))
    if locus and exclude_locations:
        raise InvalidSearchException('Cannot specify both Location and Excluded Genes/Intervals')

    genes, intervals, invalid_items = parse_locus_list_items(
        locus or exclude, genome_version=genome_version, get_genes_func=_get_genes,
    )
    if invalid_items:
        raise InvalidSearchException('Invalid genes/intervals: {}'.format(', '.join(invalid_items)))
    if (genes or intervals) and len(genes) + len(intervals) > MAX_GENES_FOR_FILTER:
        raise InvalidSearchException('Too many genes/intervals')

    exclude_intervals = None
    if exclude_locations:
        exclude_intervals = intervals
        exclude_intervals += list(genes.values())
        genes = None
        intervals = None

    search.update({
        'genes': genes, 'intervals': intervals, 'exclude_intervals': exclude_intervals, 'raw_variant_items': locus.get('rawVariantItems'),
    })
    exclude.pop('rawItems', None)


def _get_genes(gene_ids, genome_version):
    genes = GeneInfo.objects.filter(**{'gene_id__in': gene_ids, f'start_grch{genome_version}__isnull': False}).values(
        'id', 'gene_id', **{field: F(f'{field}_grch{genome_version}') for field in ['chrom', 'start', 'end']},
    )
    return {gene.pop('gene_id'): gene for gene in genes}


def _parse_dataset_type_query(genome_version, dataset_type, families, sample_data_by_dataset_type, sample_data_errors, annotate_affected_males, inheritance_mode=None, inheritance_filter=None, allow_no_samples=False, **search_kwargs):
    entry_qs = ENTRY_CLASS_MAP[genome_version][dataset_type].objects.filter_locus(inheritance_mode=inheritance_mode, **search_kwargs)
    variants_qs = VARIANTS_CLASS_MAP[genome_version][dataset_type].objects
    parsed_filters = variants_qs.get_parsed_annotations_filters(**search_kwargs)

    if dataset_type in sample_data_by_dataset_type:
        sample_data = sample_data_by_dataset_type[dataset_type]
    else:
        sample_data = _get_sample_data(
            families,
            dataset_type,
            inheritance_mode=inheritance_mode,
            inheritance_filter=inheritance_filter,
            annotate_affected_males=annotate_affected_males,
            has_location_filter=any(search_kwargs.get(field) for field in ['genes', 'intervals', 'variant_ids']),
            allow_no_samples=allow_no_samples,
        )
        sample_data_by_dataset_type[dataset_type] = sample_data

    individual_affected_status = (inheritance_filter or {}).get('affected')
    genotype_filter = (inheritance_filter or {}).get('genotype')
    if sample_data and inheritance_mode and (not sample_data['num_families'] or (individual_affected_status and all(
        (individual_affected_status.get(s['individual_guid']) or s['affected']) != AFFECTED for s in sample_data.get('samples', [])
    ))):
        sample_data_errors.add(
            'Inheritance based search is disabled in families with no data loaded for affected individuals')
        sample_data_by_dataset_type[dataset_type] = None
    if sample_data and genotype_filter and all(s['individual_guid'] not in genotype_filter for s in sample_data.get('samples', [])):
        sample_data_errors.add('Invalid custom inheritance')
        sample_data_by_dataset_type[dataset_type] = None

    return entry_qs, variants_qs, parsed_filters


def _raise_dataset_type_errors(sample_data_errors, sample_data_by_dataset_type):
    if sample_data_errors:
        raise InvalidSearchException(next(iter(sample_data_errors)))
    no_data_type = next(data_type for data_type, data in sample_data_by_dataset_type.items() if not data)
    if no_data_type.startswith(Sample.DATASET_TYPE_SV_CALLS):
        no_data_type = Sample.DATASET_TYPE_SV_CALLS
    raise InvalidSearchException(f'Unable to search against dataset type "{no_data_type}"')


def _get_search_results(entry_qs, variants_qs, sample_data, skip_entry_fields=False, **search_kwargs):
    entries = entry_qs.search(sample_data, skip_entry_fields=skip_entry_fields, **search_kwargs)
    results = variants_qs.subquery_join(entries).search(skip_entry_fields=skip_entry_fields, **search_kwargs)
    return _evaluate_results(results.result_values(skip_entry_fields=skip_entry_fields))


def _get_no_access_search_results(entry_qs, variants_qs, has_comp_het, user, **search_kwargs):
    if len(search_kwargs.get('genes') or []) != 1:
        raise InvalidSearchException('Including external projects is only available when searching for a single gene')
    if has_comp_het:
        raise InvalidSearchException('Compound heterozygous search is not supported when including external projects')
    logger.info('Looking up variants in projects with no user access', user)
    return _get_search_results(entry_qs, variants_qs, **search_kwargs, sample_data=None, skip_entry_fields=True)


def _get_x_linked_male_search_results(entry_qs, variants_qs, dataset_type, user, sample_data, **search_kwargs):
    affected_male_family_guids = {
        s['family_guid'] for s in sample_data['samples'] if s['affected'] == AFFECTED and s['sex'] in MALE_SEXES
    } if 'samples' in sample_data else sample_data['affected_male_family_guids']
    if not affected_male_family_guids:
        return []
    try:
        x_linked_entry_qs = entry_qs.filter_locus(inheritance_mode=X_LINKED_RECESSIVE_MALE_AFFECTED)
    except InvalidDatasetTypeException:
        return []

    x_linked_sample_data = _affected_male_families(sample_data, affected_male_family_guids)
    logger.info(f'Loading {dataset_type} X-linked male data for {x_linked_sample_data["num_families"]} families', user)
    return _get_search_results(
        x_linked_entry_qs, variants_qs, x_linked_sample_data, inheritance_mode=X_LINKED_RECESSIVE_MALE_AFFECTED, **search_kwargs,
    )


def _evaluate_results(result_q, is_comp_het=False):
    results = [list(result[1:]) if is_comp_het else result for result in result_q[:MAX_VARIANTS + 1]]
    if len(results) > MAX_VARIANTS:
        raise InvalidSearchException('This search returned too many results')
    return results

def _get_multi_data_type_comp_het_results(genome_version, all_families, sample_data_by_dataset_type, user, exclude_key_pairs, searched_dataset_types, annotations=None, annotations_secondary=None, **search_kwargs):
    if annotations_secondary:
        annotations = {
            **annotations,
            **{k: v + annotations[k] if annotations.get(k) else v for k, v in annotations_secondary.items()},
        }

    try:
        snv_indel_entry_qs = ENTRY_CLASS_MAP[genome_version][Sample.DATASET_TYPE_VARIANT_CALLS].objects.filter_locus(**search_kwargs)
        snv_indel_variants_qs = VARIANTS_CLASS_MAP[genome_version][Sample.DATASET_TYPE_VARIANT_CALLS].objects
        snv_indel_parsed_filters = snv_indel_variants_qs.get_parsed_annotations_filters(annotations=annotations, **search_kwargs)
        sv_variants_cls = VARIANTS_CLASS_MAP[genome_version][f'{Sample.DATASET_TYPE_SV_CALLS}_{Sample.SAMPLE_TYPE_WES}']
        sv_parsed_filters = sv_variants_cls.objects.get_parsed_annotations_filters(annotations=annotations, **search_kwargs)
    except InvalidDatasetTypeException:
        return []

    if Sample.DATASET_TYPE_VARIANT_CALLS not in sample_data_by_dataset_type:
        sample_data_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS] = _get_sample_data(
            all_families,
            Sample.DATASET_TYPE_VARIANT_CALLS,
            inheritance_mode=COMPOUND_HET,
            inheritance_filter=search_kwargs.get('inheritance_filter'),
        )
    snv_indel_sample_data = sample_data_by_dataset_type[Sample.DATASET_TYPE_VARIANT_CALLS]
    if not (snv_indel_sample_data or {}).get('num_families'):
        return []
    snv_indel_families = set().union(*snv_indel_sample_data['sample_type_families'].values())

    results = []
    for sample_type in [Sample.SAMPLE_TYPE_WES, Sample.SAMPLE_TYPE_WGS]:
        sv_dataset_type = f'{Sample.DATASET_TYPE_SV_CALLS}_{sample_type}'
        if sv_dataset_type not in sample_data_by_dataset_type:
            sample_data_by_dataset_type[sv_dataset_type] = _get_sample_data(
                all_families,
                sv_dataset_type,
                inheritance_mode=COMPOUND_HET,
                inheritance_filter=search_kwargs.get('inheritance_filter'),
            )
        sv_sample_data = sample_data_by_dataset_type[sv_dataset_type] or {}
        sv_families = set(sv_sample_data.get('sample_type_families', {}).get(sample_type, []))
        families = snv_indel_families.intersection(sv_families)
        if not families:
            continue
        logger.info(f'Loading {Sample.DATASET_TYPE_VARIANT_CALLS}/{sv_dataset_type} data for {len(families)} families', user)

        snv_indel_sample_type_families = {
            sample_type: set(familes).intersection(sv_families)
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

        entries = snv_indel_entry_qs.search(
            type_snv_indel_sample_data, inheritance_mode=COMPOUND_HET_ALLOW_HOM_ALTS, annotate_carriers=True,
            annotate_hom_alts=True, **search_kwargs,
        )
        snv_indel_q = snv_indel_variants_qs.subquery_join(entries).search(**search_kwargs, **snv_indel_parsed_filters)

        sv_entries = ENTRY_CLASS_MAP[genome_version][sv_dataset_type].objects.filter_locus(**search_kwargs).search(
            sv_sample_data, **search_kwargs, inheritance_mode=COMPOUND_HET, annotate_carriers=True,
        )
        sv_variants_cls = VARIANTS_CLASS_MAP[genome_version][sv_dataset_type]
        sv_q = sv_variants_cls.objects.subquery_join(sv_entries).search(**search_kwargs, **sv_parsed_filters)

        result_q = _get_comp_het_results_queryset(
            snv_indel_variants_qs, snv_indel_q, sv_q, len(families),
            exclude_key_pairs=exclude_key_pairs.get(f'{Sample.DATASET_TYPE_VARIANT_CALLS},{sv_dataset_type}'),
        )
        dataset_results = _evaluate_results(result_q, is_comp_het=True)
        if not sv_sample_data['samples']:
            _add_individual_guids(dataset_results)
        results += dataset_results
        searched_dataset_types.add(sv_dataset_type)

    if not searched_dataset_types:
        raise InvalidSearchException(
            'Unable to search for comp-het pairs with dataset type "SV". This may be because inheritance based search is disabled in families with no loaded affected individuals'
        )

    return results


def _get_data_type_comp_het_results_queryset(entry_qs, variants_qs, sample_data, user, parsed_filters, is_x_chrom=False, annotations_secondary=None, exclude_key_pairs=None, **search_kwargs):
    if not any(parsed_filters.values()):
        raise InvalidSearchException('Annotations must be specified to search for compound heterozygous variants')

    parsed_secondary_filters = {}
    if annotations_secondary:
        try:
            parsed_secondary_filters = variants_qs.get_parsed_annotations_filters(annotations=annotations_secondary)
        except InvalidDatasetTypeException:
            return []

    if is_x_chrom and 'affected_male_family_guids' in sample_data:
        sample_data = _no_affected_male_families(sample_data, user)

    entries = entry_qs.search(
        sample_data, **search_kwargs, **parsed_filters, inheritance_mode=COMPOUND_HET, annotate_carriers=True,
    )

    primary_q = variants_qs.subquery_join(entries).search(**search_kwargs, **parsed_filters)
    secondary_kwargs = {**search_kwargs, **parsed_filters, **parsed_secondary_filters}
    secondary_q = variants_qs.subquery_join(entries).search(**secondary_kwargs)

    result_q = _get_comp_het_results_queryset(variants_qs, primary_q, secondary_q, sample_data['num_families'], exclude_key_pairs)
    return _evaluate_results(result_q, is_comp_het=True) if result_q is not None else []


def _get_comp_het_results_queryset(variants_qs, primary_q, secondary_q, num_families, exclude_key_pairs):
    results = variants_qs.search_compound_hets(primary_q, secondary_q)

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
        results = results.annotate(calc_pos=Modulo('primary_xpos', int(1e9)))
        is_overlapped_del = Q(secondary_svType='DEL', calc_pos__gte=F('secondary_pos'),  calc_pos__lte=F('secondary_end'))
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


def _add_individual_guids(results, encode_genotypes_json=False):
    families = set()
    for result in results:
        for r in (result if isinstance(result, list) else [result]):
            families.update(r.get('familyGenotypes', {}).keys())
    sample_map = {
        (family_guid, sample_id): individual_guid for family_guid, individual_guid, sample_id in Sample.objects.filter(
            individual__family__guid__in=families, is_active=True,
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


def get_sorted_search_results(results, sort, families):
    sort_metadata = _get_sort_gene_metadata(sort, results, families)
    sort_key = _get_sort_key(sort, sort_metadata)
    sorted_results = sorted([
        sorted(result, key=sort_key) if isinstance(result, list) else result for result in results
    ], key=sort_key)
    return sorted_results


def format_clickhouse_export_results(results):
    formatted_results = [variant for result in results for variant in (result if isinstance(result, list) else [result])]
    if not formatted_results:
        return []

    genome_version = formatted_results[0]['genomeVersion']
    keys_with_no_details = {result['key'] for result in formatted_results if not 'transcripts' in result}
    detail_qs = get_variant_details_queryset(genome_version, Sample.DATASET_TYPE_VARIANT_CALLS, keys_with_no_details)
    details_by_key = {
        detail['key']: detail for detail in detail_qs.values(
            'key', 'rsid', mainTranscript=F('transcripts__0'), variantId=F('variant_id'),
            **detail_qs.split_variant_id_annotations(),
        )
    }

    gene_ids = set()
    for result in formatted_results:
        if 'transcripts' in result:
            result['mainTranscript'] = next((gene_transcripts[0] for gene_transcripts in result['transcripts'].values()), {})
        else:
            result.update(details_by_key.get(result['key'], {}))
        if result.get('mainTranscript'):
            gene_ids.add(result['mainTranscript']['geneId'])

    gene_id_map = dict(GeneInfo.objects.filter(gene_id__in=gene_ids).values_list('gene_id', 'gene_symbol'))
    for result in formatted_results:
        if result.get('mainTranscript'):
            result['geneSymbol'] = gene_id_map.get(result['mainTranscript']['geneId'])

    return formatted_results


def format_clickhouse_results(results):
    if not results:
        return []

    genome_version = (results[0] if isinstance(results[0], list) else results)[0]['genomeVersion']
    keys_with_no_details = {
        variant['key'] for result in results for variant in (result if isinstance(result, list) else [result]) if not 'transcripts' in variant
    }
    details_by_key = {
        detail['key']: detail for detail in
        get_variant_details_queryset(genome_version, Sample.DATASET_TYPE_VARIANT_CALLS, keys_with_no_details).result_values()
    }

    formatted_results = []
    for variant in results:
        if isinstance(variant, list):
            formatted_result = [_format_variant(v, details_by_key) for v in variant]
        else:
            formatted_result = _format_variant(variant, details_by_key)
        formatted_results.append(formatted_result)

    return formatted_results


def _format_variant(variant, details_by_key):
    formatted_variant = {**variant}
    selected_gene_id = formatted_variant.pop(SELECTED_GENE_FIELD, None)
    selected_transcript = formatted_variant.pop(SELECTED_TRANSCRIPT_FIELD, None)
    if 'transcripts' in variant:
        return formatted_variant

    details = details_by_key.get(variant['key'], {})
    formatted_variant.update(details)

    # pop sortedTranscriptConsequences from the formatted result and not the original result to ensure the full value is cached properly
    sorted_minimal_transcripts = formatted_variant.pop(TRANSCRIPT_CONSEQUENCES_FIELD)
    main_transcript_id = None
    selected_main_transcript_id = None
    if sorted_minimal_transcripts:
        main_transcript_id = next(
            t['transcriptId'] for t in details['transcripts'][sorted_minimal_transcripts[0]['geneId']]
            if t['transcriptRank'] == 0
        )
    if selected_transcript:
        selected_main_transcript_id = next(
            t['transcriptId'] for t in details['transcripts'][selected_transcript['geneId']]
            if _is_matched_minimal_transcript(t, selected_transcript)
        )
    elif selected_gene_id:
        selected_main_transcript_id = details['transcripts'][selected_gene_id][0]['transcriptId']
    return {
        **formatted_variant,
        'mainTranscriptId': main_transcript_id,
        'selectedMainTranscriptId': None if selected_main_transcript_id == main_transcript_id else selected_main_transcript_id,
    }


def _is_matched_minimal_transcript(transcript, minimal_transcript):
    return (all(transcript[field] == minimal_transcript[field] for field in ['canonical','consequenceTerms'])
     and transcript.get('utrannotator', {}).get('fiveutrConsequence') == minimal_transcript.get('fiveutrConsequence')
     and transcript.get('spliceregion', {}).get('extended_intronic_splice_region_variant') == minimal_transcript.get('extendedIntronicSpliceRegionVariant'))


def _get_valid_samples(families, dataset_type, sample_type, allow_no_samples):
    samples = Sample.objects.filter(individual__family__in=families, is_active=True)
    if not samples.exists():
        if allow_no_samples:
            return None
        raise InvalidSearchException(f'No search data found for families {", ".join([f.family_id for f in families])}')

    samples = samples.filter(dataset_type=dataset_type)
    if sample_type:
        samples = samples.filter(sample_type=sample_type)

    mismatch_affected_samples = samples.values('sample_id').annotate(
        projects=ArrayAgg('individual__family__project__name', distinct=True),
        affected=ArrayAgg('individual__affected', distinct=True),
    ).filter(affected__len__gt=1)
    if mismatch_affected_samples:
        raise InvalidSearchException(
            'The following samples are incorrectly configured and have different affected statuses in different projects: ' +
            ', '.join([f'{agg["sample_id"]} ({"/ ".join(agg["projects"])})' for agg in mismatch_affected_samples]),
        )

    return samples


def _get_sample_metadata(samples, affected_family_only, annotate_affected_males):
    skip_individual_guid = samples.values('individual__family__project_id').distinct().count() > 1
    family_array_kwargs = {'distinct': True}
    if affected_family_only:
        family_array_kwargs['filter'] = Q(individual__affected=Individual.AFFECTED_STATUS_AFFECTED)
    annotations = {
        'project_guids': ArrayAgg('individual__family__project__guid', distinct=True),
        'family_guids': ArrayAgg('individual__family__guid', **family_array_kwargs),
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
            affected='individual__affected', sex='individual__sex', sample_id='sample_id', sample_type='sample_type',
            family_guid=F('individual__family__guid'), individual_guid=F('individual__guid'),
        ))

    return samples.aggregate(**annotations)


def _get_sample_data(families, dataset_type, annotate_affected_males=False, allow_no_samples=False, inheritance_mode=None, inheritance_filter=None, has_location_filter=False):
    sample_type = None
    if dataset_type.startswith(Sample.DATASET_TYPE_SV_CALLS):
        dataset_type, sample_type = dataset_type.split('_')
    samples = _get_valid_samples(families, dataset_type, sample_type, allow_no_samples)
    if not samples:
        return {}

    individual_affected_status = (inheritance_filter or {}).get('affected')
    affected_family_only = inheritance_mode and not individual_affected_status
    sample_data = _get_sample_metadata(samples, affected_family_only, annotate_affected_males)

    family_guids = set(sample_data.pop('family_guids'))
    if not has_location_filter:
        if len(sample_data['project_guids']) > 1:
            raise InvalidSearchException('Location must be specified to search across multiple projects')
        if inheritance_mode in {RECESSIVE, COMPOUND_HET} and len(family_guids) > MAX_NO_LOCATION_COMP_HET_FAMILIES:
            raise InvalidSearchException(
                'Location must be specified to search for compound heterozygous variants across many families',
            )

    sample_data['num_families'] = len(family_guids)
    if sample_type:
        sample_data['sample_type_families'] = {sample_type: family_guids}
    else:
        if sample_data.get('samples'):
            sample_data['sample_type_families'] = defaultdict(set)
            for sample in sample_data['samples']:
                sample_data['sample_type_families'][sample['sample_type']].add(sample['family_guid'])
        else:
            sample_data['sample_type_families'] = dict(
                samples.filter(individual__family__guid__in=family_guids).values('sample_type').values_list(
                    'sample_type', ArrayAgg('individual__family__guid', distinct=True),
                )
            )
        if len(sample_data['sample_type_families']) == 2:
            st_families_1, st_families_2 = sample_data['sample_type_families'].values()
            multi_families = set(st_families_1).intersection(st_families_2)
            if multi_families:
                sample_data['sample_type_families'] = {
                    sample_type: set(families) - multi_families
                    for sample_type, families in sample_data['sample_type_families'].items()
                    if set(families) - multi_families
                }
                sample_data['sample_type_families']['multi'] = multi_families
                _add_missing_multi_type_samples(samples, sample_data)

    return sample_data


def _add_missing_multi_type_samples(samples, data):
    data['family_missing_type_samples'] = defaultdict(lambda: defaultdict(list))
    if 'samples'  in data:
        individual_sample_types = defaultdict(list)
        for s in data['samples']:
            individual_sample_types[s['individual_guid']].append(s)
        individual_samples = [
            {'samples': samples, 'family_guid': samples[0]['family_guid']}
            for samples in individual_sample_types.values() if len(samples) == 1
        ]
    else:
        individual_samples = samples.filter(individual__family__guid__in=data['sample_type_families']['multi'],
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


def _is_x_chrom_only(genes=None, intervals=None, **kwargs):
    if not (genes or intervals):
        return False
    return all('X' in interval['chrom'] for interval in list((genes or {}).values()) + (intervals or []))


def _has_x_chrom(genes=None, intervals=None, **kwargs):
    if not (genes or intervals):
        return True
    return any('X' in interval['chrom'] for interval in list((genes or {}).values()) + (intervals or []))


def _prioritized_gene_sort(gene_ids, families):
    if len(families) != 1:
        raise InvalidSearchException('Phenotype sort is only supported for single-family search.')
    return {
        agg['gene_id']: agg['min_rank'] for agg in PhenotypePrioritization.objects.filter(
            gene_id__in=gene_ids, individual__family_id=families[0].id, rank__lte=100,
        ).values('gene_id').annotate(min_rank=Min('rank'))
    }


OMIM_SORT = 'in_omim'
GENE_SORTS = {
    'constraint': lambda gene_ids, _: {
        agg['gene__gene_id']: agg['mis_z_rank'] + agg['pLI_rank'] for agg in
        GeneConstraint.objects.filter(gene__gene_id__in=gene_ids).values('gene__gene_id', 'mis_z_rank', 'pLI_rank')
    },
    OMIM_SORT: lambda gene_ids, _: set(Omim.objects.filter(
        gene__gene_id__in=gene_ids, phenotype_mim_number__isnull=False,
    ).values_list('gene__gene_id', flat=True)),
    PRIORITIZED_GENE_SORT: _prioritized_gene_sort,
}

def _get_sort_gene_metadata(sort, results, families):
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
    return get_metadata(gene_ids, families)


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
HGMD_RANK_LOOKUP = {class_: rank for rank, class_ in BaseHgmd.HGMD_CLASSES}
ABSENT_CLINVAR_SORT_OFFSET = 12.5
CONSEQUENCE_RANK_LOOKUP = {csq: rank for rank, csq in BaseVariants.CONSEQUENCE_TERMS}
SV_CONSEQUENCE_LOOKUP = {csq: rank for rank, csq in BaseVariantsSvGcnv.SV_CONSEQUENCE_RANKS}
PREDICTION_SORTS = {'cadd', 'revel', 'splice_ai', 'eigen', 'mpc', 'primate_ai'}
CLINVAR_SORT =  _subfield_sort(
    'clinvar', 'pathogenicity', rank_lookup=CLINVAR_RANK_LOOKUP, default=ABSENT_CLINVAR_SORT_OFFSET,
)
SORT_EXPRESSIONS = {
    'alphamissense': [
        lambda x: -max(t.get('alphamissensePathogenicity') or MIN_SORT_RANK for t in x[TRANSCRIPT_CONSEQUENCES_FIELD]) if x.get(TRANSCRIPT_CONSEQUENCES_FIELD) else MIN_SORT_RANK,
    ] + _subfield_sort(SELECTED_TRANSCRIPT_FIELD, 'alphamissensePathogenicity', reverse=True, default=MIN_SORT_RANK),
    'callset_af': _subfield_sort('populations', ('seqr', 'sv_callset'), 'ac'),
    'family_guid': [lambda x: sorted(x.get('familyGuids', ['z']))[0]],
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


def _clickhouse_variant_lookup(entries, genome_version, data_type, affected_only=False, hom_only=False):
    variants_cls = VARIANTS_CLASS_MAP[genome_version][data_type]

    entries = _filter_lookup_entries(entries, affected_only, hom_only)
    entries = entries.result_values()
    results = variants_cls.objects.subquery_join(entries)
    if hasattr(results, 'add_genotype_override_annotations'):
        results = results.add_genotype_override_annotations(results)

    variant = results.result_values().first()
    if variant:
        variant = format_clickhouse_results([variant])[0]
    return variant

def _filter_lookup_entries(entries, affected_only, hom_only):
    if affected_only:
        entries = entries.filter(entries.any_affected_q())
    if hom_only:
        entries = entries.filter(calls__array_exists={'gt': (2,)})
    return entries

def clickhouse_variant_lookup(user, variant_id, sample_type, genome_version, affected_only, hom_only):
    data_type = entry_qs = None
    for dataset_type, entry_cls in sorted(ENTRY_CLASS_MAP[genome_version].items()):
        try:
            entry_qs = entry_cls.objects.filter_locus(
                variant_ids=[variant_id], raw_variant_items=variant_id,
            )
        except InvalidDatasetTypeException:
            continue
        if dataset_type.startswith(Sample.DATASET_TYPE_SV_CALLS):
            if not sample_type:
                raise InvalidSearchException('Sample type must be specified to look up a structural variant')
            elif not dataset_type.endswith(sample_type):
                continue
        data_type = dataset_type
        break
    if data_type is None:
        raise InvalidSearchException('Invalid genome build for dataset type')

    logger.info(f'Looking up variant {variant_id} with data type {data_type}', user)

    variant = _clickhouse_variant_lookup(
        entry_qs, genome_version, data_type, affected_only=affected_only, hom_only=hom_only,
    )
    if variant:
        _add_liftover_genotypes(variant, data_type, variant_id, affected_only, hom_only)
    else:
        lifted_genome_version = next(gv for gv in ENTRY_CLASS_MAP.keys() if gv != genome_version)
        lifted_entry_cls = ENTRY_CLASS_MAP[lifted_genome_version].get(data_type)
        if lifted_entry_cls:
            from seqr.utils.search.utils import run_liftover
            chrom, pos, _ = variant_id.split('-', 2)
            liftover_results = run_liftover(lifted_genome_version, chrom, int(pos))
            if liftover_results:
                lifted_id = variant_id.replace(pos, str(liftover_results[1]))
                entry_qs = lifted_entry_cls.objects.filter_locus(raw_variant_items=lifted_id)
                variant = _clickhouse_variant_lookup(
                    entry_qs, lifted_genome_version, data_type, affected_only=affected_only, hom_only=hom_only,
                )

    if not variant:
        raise ObjectDoesNotExist('Variant not present in seqr')

    variants = [variant]

    if variant.get('svType') in {'DEL', 'DUP'}:
        other_sample_type, other_entry_class = next(
            (dt, cls) for dt, cls in ENTRY_CLASS_MAP[genome_version].items()
            if dt != data_type and dt.startswith(Sample.DATASET_TYPE_SV_CALLS)
        )
        other_variants_cls = VARIANTS_CLASS_MAP[genome_version][other_sample_type]

        padding = int((variant['end'] - variant['pos']) * 0.2)
        entries = other_entry_class.objects.search_padded_interval(variant['chrom'], variant['pos'], padding)
        entries = _filter_lookup_entries(entries, affected_only, hom_only)
        results = other_variants_cls.objects.subquery_join(entries).search(
            padded_interval_end=(variant['end'], padding), **other_variants_cls.objects.get_parsed_annotations_filters(
                annotations={'structural': [variant['svType'], f"gCNV_{variant['svType']}"]},
            ),
        )
        variants += list(results.result_values())

    return variants


def _add_liftover_genotypes(variant, data_type, variant_id, affected_only, hom_only):
    lifted_entry_cls = ENTRY_CLASS_MAP.get(variant.get('liftedOverGenomeVersion'), {}).get(data_type)
    if not (lifted_entry_cls and variant.get('liftedOverChrom') and variant.get('liftedOverPos')):
        return
    lifted_id = variant_id.replace(str(variant['pos']), str(variant['liftedOverPos']))
    lifted_entries = lifted_entry_cls.objects.filter_locus(raw_variant_items=lifted_id)
    lifted_entries = _filter_lookup_entries(lifted_entries, affected_only, hom_only)
    gt_field, gt_expr = lifted_entry_cls.objects.genotype_expression()
    lifted_entry_data = lifted_entries.values('key').annotate(**{gt_field: GroupArrayArray(gt_expr)})
    if lifted_entry_data:
        variant['familyGenotypes'].update(lifted_entry_data[0]['familyGenotypes'])
        variant['liftedFamilyGuids'] = sorted(lifted_entry_data[0]['familyGenotypes'].keys())


def get_clickhouse_genotypes(project_guid, family_guids, genome_version, dataset_type, keys, additional_fields=None):
    sample_data = _get_sample_data(Family.objects.filter(guid__in=family_guids), dataset_type)
    entries = ENTRY_CLASS_MAP[genome_version][dataset_type].objects.filter(
        project_guid=project_guid, family_guid__in=family_guids, key__in=keys,
    )
    gt_field, gt_expr = entries.genotype_expression(sample_data)
    return {
        e['key']: {**e, 'genotypes': _clickhouse_genotypes_json(e['genotypes'])} for e in
        entries.annotate(**{gt_field: gt_expr}).values('key', 'genotypes', *(additional_fields or []))
    }


def _clickhouse_genotypes_json(genotypes):
    return json.loads(json.dumps(genotypes, cls=DjangoJSONEncoderWithSets))


def get_variants_queryset(genome_version, dataset_type, keys, variant_ids=None):
    variants_cls = VARIANTS_CLASS_MAP[genome_version][dataset_type]
    if variant_ids:
        return variants_cls.objects.filter_variant_ids(variant_ids)
    return variants_cls.objects.filter(key__in=keys)


def get_variant_details_queryset(genome_version, dataset_type, keys):
    if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
        return VARIANT_DETAILS_CLASS_MAP[genome_version].objects.filter(key__in=keys)
    return get_variants_queryset(genome_version, dataset_type, keys)


def get_clickhouse_variant_annotations(genome_version, dataset_type, keys):
    qs = get_variant_details_queryset(genome_version, dataset_type, keys)
    return qs.join_annotations().result_values(skip_entry_fields=True)


def get_clickhouse_key_lookup(genome_version, dataset_type, variants_ids):
    key_lookup_class = ENTRY_CLASS_MAP[genome_version][dataset_type].objects.none().key_lookup_model
    lookup = {}
    fields = ('variant_id', 'key')
    for i in range(0, len(variants_ids), BATCH_SIZE):
        batch = variants_ids[i:i + BATCH_SIZE]
        lookup.update(dict(key_lookup_class.objects.filter(variant_id__in=batch).values_list(*fields)))
    return lookup


def _main_transcript(selected_transcript_id, sorted_transcripts):
    if not sorted_transcripts:
        return {}
    if selected_transcript_id:
        return next((t for t in sorted_transcripts if t['transcriptId'] == selected_transcript_id), {})
    return sorted_transcripts[0]


def delete_clickhouse_project(project, dataset_type, sample_type=None):
    if dataset_type == Sample.DATASET_TYPE_SV_CALLS and sample_type == Sample.SAMPLE_TYPE_WES:
        dataset_type = 'GCNV'
    table_base = f'{GENOME_VERSION_LOOKUP[project.genome_version]}/{dataset_type}'
    with connections['clickhouse_write'].cursor() as cursor:
        cursor.execute(f'ALTER TABLE "{table_base}/entries" DROP PARTITION %s', [project.guid])
        if dataset_type != 'GCNV':
            cursor.execute(f'ALTER TABLE "{table_base}/project_gt_stats" DROP PARTITION %s', [project.guid])
            PROJECT_GT_STATS_VIEW_CLASS_MAP[project.genome_version][dataset_type].refresh()
            ENTRY_CLASS_MAP[project.genome_version][dataset_type].gt_stats.rel.related_model.reload()
    return f'Deleted all {dataset_type} search data for project {project.name}'
