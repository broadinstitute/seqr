import json
import jmespath
from collections import defaultdict
from copy import deepcopy
from datetime import timedelta
from django.utils import timezone
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import MultipleObjectsReturned, PermissionDenied
from django.db.utils import IntegrityError
from django.db.models import Q, F, Value, Count
from django.db.models.functions import JSONObject
from django.shortcuts import redirect
from math import ceil
import re

from clickhouse_search.constants import XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY
from clickhouse_search.search import get_clickhouse_variants, format_clickhouse_results, format_clickhouse_export_results, \
    get_sorted_search_results, clickhouse_variant_lookup, InvalidSearchException
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_LOOKUP
from seqr.models import Project, Family, Individual, SavedVariant, VariantSearch, VariantSearchResults, ProjectCategory, Sample
from seqr.views.utils.export_utils import export_table
from seqr.utils.gene_utils import get_genes_for_variant_display
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_get_wildcard_json, safe_redis_set_json
from seqr.utils.xpos_utils import parse_variant_id
from seqr.views.utils.json_utils import create_json_response, _to_snake_case
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json, \
    create_model_from_json
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants_with_tags, get_json_for_saved_search,\
    get_json_for_saved_searches, add_individual_hpo_details, FAMILY_ADDITIONAL_VALUES
from seqr.views.utils.permissions_utils import check_project_permissions, get_project_guids_user_can_view, \
    login_and_policies_required, check_user_created_object_permissions, check_projects_view_permission, user_is_analyst
from seqr.views.utils.project_context_utils import get_projects_child_entities
from seqr.views.utils.variant_utils import get_variants_response, variant_dataset_type
from seqr.views.utils.vlm_utils import vlm_lookup

logger = SeqrLogger(__name__)


GENOTYPE_AC_LOOKUP = {
    'ref_ref': [0, 0],
    'has_ref': [0, 1],
    'ref_alt': [1, 1],
    'has_alt': [1, 2],
    'alt_alt': [2, 2],
}
AFFECTED = Individual.AFFECTED_STATUS_AFFECTED
UNAFFECTED = Individual.AFFECTED_STATUS_UNAFFECTED


@login_and_policies_required
def query_variants_handler(request, search_hash):
    """Search variants.
    """
    page = int(request.GET.get('page') or 1)
    per_page = int(request.GET.get('per_page') or 100)
    sort = request.GET.get('sort') or XPOS_SORT_KEY
    if sort == PATHOGENICTY_SORT_KEY and user_is_analyst(request.user):
        sort = PATHOGENICTY_HGMD_SORT_KEY

    search_context = json.loads(request.body or '{}')
    try:
        results_model = _get_or_create_results_model(search_hash, search_context, request.user)
    except Exception as e:
        return create_json_response({'error': str(e)}, status=400, reason=str(e))

    _check_results_permission(results_model, request.user)

    all_variants = _get_variants_with_cache(
        _get_search_cache_key, _query_variants, results_model, request.user, sort=sort,
    )
    variants = all_variants[(page-1)*per_page:page*per_page]

    response = _process_variants(variants or [], results_model.families.all(), request,
                                 genome_version=results_model.variant_search.search.get('no_access_project_genome_version'))
    response['search'] = _get_search_context(results_model)
    response['search']['totalResults'] = len(all_variants)

    return create_json_response(response)


def _get_variants_with_cache(get_cache_key, get_variants, *args, **kwargs):
    cache_key = get_cache_key(*args, **kwargs)
    variants = safe_redis_get_json(cache_key)
    if variants is None:
        variants = get_variants(*args, **kwargs)
        safe_redis_set_json(cache_key, variants, expire=timedelta(weeks=2))
    return variants


def _get_search_cache_key(results_model, user, sort=XPOS_SORT_KEY):
    return 'search_results__{}__{}'.format(results_model.guid, sort)


def _query_variants(results_model, user, sort=XPOS_SORT_KEY):
    families = results_model.families.all()
    wildcard_cache_key = _get_search_cache_key(results_model, user, sort='*')
    unsorted_variants = safe_redis_get_wildcard_json(wildcard_cache_key)
    if unsorted_variants:
        return get_sorted_search_results(unsorted_variants, sort, families)

    return get_clickhouse_variants(families, user, sort=sort, **results_model.variant_search.search)


def _all_project_family_search_genome(search_context):
    return (search_context or {}).get('allGenomeProjectFamilies')


def _all_genome_version_families(genome_version, user):
    omit_projects = [p.guid for p in Project.objects.filter(is_demo=True).only('guid')]
    project_guids = [
        project_guid for project_guid in get_project_guids_user_can_view(user, limit_data_manager=True)
        if project_guid not in omit_projects
    ]
    return Family.objects.filter(project__guid__in=project_guids, project__genome_version=genome_version)


def _get_or_create_results_model(search_hash, search_context, user):
    results_model = VariantSearchResults.objects.filter(search_hash=search_hash).first()
    if not results_model:
        if not search_context:
            raise Exception('Invalid search hash: {}'.format(search_hash))

        all_project_genome_version = _all_project_family_search_genome(search_context)
        include_no_access_projects = search_context.get('includeNoAccessProjects')
        if all_project_genome_version:
            families = _all_genome_version_families(all_project_genome_version, user)
            if not (families or include_no_access_projects):
                raise Exception(f'No data available for genome version "{GENOME_VERSION_LOOKUP[all_project_genome_version]}"')
        elif search_context.get('projectFamilies'):
            all_families = set()
            for project_family in search_context['projectFamilies']:
                all_families.update(project_family['familyGuids'])
            families = Family.objects.filter(guid__in=all_families)
        else:
            raise Exception('Invalid search: no projects/ families specified')

        if search_context.get('unsolvedFamiliesOnly'):
            families = families.exclude(analysis_status__in=Family.SOLVED_ANALYSIS_STATUSES)
        if search_context.get('trioFamiliesOnly'):
            families = families.annotate(search_sample_count=Count('individual__sample__id', filter=Q(
                individual__sample__is_active=True, individual__sample__dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
            ))).filter(
                search_sample_count__gte=3, individual__mother__isnull=False, individual__father__isnull=False,
            ).distinct()

        search_dict = search_context.get('search', {})
        if search_context.get('previousSearchHash') and (search_dict.get('exclude') or {}).get('previousSearch'):
            search_dict.update(_get_exclude_keys(search_context['previousSearchHash'], user))
        if include_no_access_projects:
            search_dict['no_access_project_genome_version'] = all_project_genome_version
        search_model = VariantSearch.objects.filter(search=search_dict).filter(
            Q(created_by=user) | Q(name__isnull=False)).first()
        if not search_model:
            search_model = create_model_from_json(VariantSearch, {'search': search_dict}, user)

        # If a search_context request and results request are dispatched at the same time, its possible the other
        # request already created the model
        results_model = VariantSearchResults.objects.filter(search_hash=search_hash).first()
        if not results_model:
            results_model = create_model_from_json(
                VariantSearchResults, {'search_hash': search_hash, 'variant_search': search_model}, user)

        results_model.families.set(families)
    return results_model


def _get_exclude_keys(search_hash, user):
    previous_results_model = VariantSearchResults.objects.get(search_hash=search_hash)
    results = _get_variants_with_cache(_get_search_cache_key, _query_variants, previous_results_model, user)
    exclude_keys = defaultdict(list)
    exclude_key_pairs = defaultdict(list)
    for variant in results:
        if isinstance(variant, list):
            dt1= variant_dataset_type(variant[0])
            dt2 = variant_dataset_type(variant[1])
            dataset_type = dt1 if dt1 == dt2 else ','.join(sorted([dt1, dt2]))
            exclude_key_pairs[dataset_type].append(sorted([variant[0]['key'], variant[1]['key']]))
        else:
            dataset_type = variant_dataset_type(variant)
            exclude_keys[dataset_type].append(variant['key'])
    return {'exclude_keys': dict(exclude_keys), 'exclude_key_pairs': dict(exclude_key_pairs)}


@login_and_policies_required
def query_single_variant_handler(request, variant_id):
    """Search variants.
    """
    families = Family.objects.filter(guid=request.GET.get('familyGuid'))
    family = families.first()
    check_project_permissions(family.project, request.user)

    variants = get_clickhouse_variants(families, request.user, raw_variant_items=variant_id, variant_ids=[variant_id])
    if not variants:
        raise InvalidSearchException('Variant {} not found'.format(variant_id))

    response = _process_variants(variants, families, request, add_all_context=True, add_locus_list_detail=True)

    return create_json_response(response)


def _process_variants(variants, families, request, add_all_context=False, add_locus_list_detail=False, genome_version=None):
    if not variants:
        return {'searchedVariantIds': [], 'variantsById': {}}

    variants = format_clickhouse_results(variants)
    flat_variants = _flatten_variants(variants)
    variants_by_id = {v['variantId']: v for v in flat_variants}
    saved_variants = _get_saved_variant_models(flat_variants)

    response_json = get_variants_response(
        request, saved_variants, response_variants=flat_variants, add_all_context=add_all_context,
        add_locus_list_detail=add_locus_list_detail, genome_version=genome_version or families[0].project.genome_version)
    response_json['searchedVariantIds'] = [
        [v['variantId'] for v in variant] if isinstance(variant, list) else variant['variantId'] for variant in variants
    ]

    for saved_variant in response_json['savedVariantsByGuid'].values():
        family_guids = saved_variant['familyGuids']
        searched_variant = variants_by_id.get(saved_variant['variantId'])
        if not searched_variant:
            # This can occur when an hg38 family has a saved variant that did not successfully lift from hg37
            continue
        saved_variant.update(searched_variant)
        #  For saved variants only use family it was saved for, not all families in search
        saved_variant['familyGuids'] = family_guids
        response_json['savedVariantsByGuid'][saved_variant['variantGuid']] = saved_variant

    return response_json


MUTTASTR_MAP = {
    'A': 'disease_causing',
    'D': 'disease_causing',
    'N': 'polymorphism',
    'P': 'polymorphism',
}


VARIANT_EXPORT_DATA = [
    {'header': 'chrom'},
    {'header': 'pos'},
    {'header': 'ref'},
    {'header': 'alt'},
    {'header': 'gene', 'value_path': 'mainTranscript.geneId'},
    {'header': 'gene_symbol', 'value_path': 'geneSymbol'},
    {'header': 'worst_consequence', 'value_path': 'mainTranscript.majorConsequence'},
    {'header': 'seqr_ac', 'value_path': 'populations.seqr.ac'},
    {'header': 'gnomad_genomes_freq', 'value_path': 'populations.gnomad_genomes.af'},
    {'header': 'gnomad_exomes_freq', 'value_path': 'populations.gnomad_exomes.af'},
    {'header': 'topmed_freq', 'value_path': 'populations.topmed.af'},
    {'header': 'cadd', 'value_path': 'predictions.cadd'},
    {'header': 'revel', 'value_path': 'predictions.revel'},
    {'header': 'eigen', 'value_path': 'predictions.eigen'},
    {'header': 'splice_ai', 'value_path': 'predictions.splice_ai'},
    {'header': 'polyphen', 'value_path': 'predictions.polyphen'},
    {'header': 'sift', 'value_path': 'predictions.sift'},
    {'header': 'muttaster', 'value_path': 'predictions.mut_taster', 'process': MUTTASTR_MAP.get},
    {'header': 'fathmm', 'value_path': 'predictions.fathmm'},
    {'header': 'rsid', 'value_path': 'rsid'},
    {'header': 'hgvsc', 'value_path': 'mainTranscript.hgvsc'},
    {'header': 'hgvsp', 'value_path': 'mainTranscript.hgvsp'},
    {'header': 'clinvar_clinical_significance', 'value_path': 'clinvar.pathogenicity'},
    {'header': 'clinvar_gold_stars', 'value_path': 'clinvar.goldStars'},
]

VARIANT_FAMILY_EXPORT_DATA = [
    {'header': 'family_id'},
    {'header': 'tags', 'process': lambda tags: '|'.join([
        '{} ({})'.format(tag['name'], tag['createdBy']) for tag in
        sorted(tags or [], key=lambda tag: tag['lastModifiedDate'] or timezone.now(), reverse=True)
    ])},
    {'header': 'notes', 'process': lambda notes: '|'.join([
        '{} ({})'.format(note['note'].replace('\n', ' '), note['createdBy']) for note in
        sorted(notes or [], key=lambda note: note['lastModifiedDate'] or timezone.now(), reverse=True)
    ])},
]

VARIANT_SAMPLE_DATA = [
    {'header': 'sample', 'value_path': 'sampleId'},
    {'header': 'num_alt_alleles', 'value_path': 'numAlt'},
    {'header': 'filters', 'process': lambda val: ';'.join(val or [])},
    {'header': 'gq'},
    {'header': 'ab'},
]

MAX_EXPORT_VARIANTS = 1000
MAX_FAMILIES_PER_ROW = 1000


@login_and_policies_required
def get_variant_gene_breakdown(request, search_hash):
    results_model = VariantSearchResults.objects.get(search_hash=search_hash)
    projects = _check_results_permission(results_model, request.user)

    results = _get_variants_with_cache(_get_search_cache_key, _query_variants, results_model, request.user)
    flat_variants = [
        v for variants in results for v in (variants if isinstance(variants, list) else [variants])
    ]
    gene_counts = defaultdict(lambda: {'total': 0, 'families': defaultdict(int)})
    for var in flat_variants:
        gene_ids = var['transcripts'].keys() if 'transcripts' in var else {t['geneId'] for t in var['sortedTranscriptConsequences']}
        for gene_id in gene_ids:
            gene_counts[gene_id]['total'] += 1
            for family_guid in var['familyGuids']:
                gene_counts[gene_id]['families'][family_guid] += 1

    return create_json_response({
        'searchGeneBreakdown': {search_hash: gene_counts},
        'genesById': get_genes_for_variant_display(list(gene_counts.keys()), projects.first().genome_version),
    })


@login_and_policies_required
def export_variants_handler(request, search_hash):
    results_model = VariantSearchResults.objects.get(search_hash=search_hash)

    _check_results_permission(
        results_model, request.user, project_perm_check=lambda project: (not project.is_demo) or project.all_user_demo)

    families = results_model.families.all()
    family_ids_by_guid = {family.guid: family.family_id for family in families}

    variants = _get_variants_with_cache(_get_search_cache_key, _query_variants, results_model, request.user)
    total_variants = len(variants)
    if total_variants > MAX_EXPORT_VARIANTS:
        raise InvalidSearchException(f'Unable to export more than {MAX_EXPORT_VARIANTS} variants ({total_variants} requested)')

    variants = format_clickhouse_export_results(variants)

    saved_variants = _get_saved_variant_models(variants)
    json_saved_variants = get_json_for_saved_variants_with_tags(saved_variants)

    saved_variants_by_variant_family = {}
    for saved_variant in json_saved_variants['savedVariantsByGuid'].values():
        saved_variants_by_variant_family[saved_variant['variantId']] = {
            family_guid: saved_variant['variantGuid'] for family_guid in saved_variant['familyGuids']
        }

    if any(len(variant.get('familyGuids', [])) > MAX_FAMILIES_PER_ROW for variant in variants):
        split_variants = []
        for variant in variants:
            if len(variant.get('familyGuids', [])) <= MAX_FAMILIES_PER_ROW:
                split_variants.append(variant)
                continue

            num_split = ceil(len(variant.get('familyGuids', [])) / MAX_FAMILIES_PER_ROW)
            gens_per_row = ceil(len(variant['genotypes']) / num_split)
            gen_keys = sorted(variant['genotypes'].keys())
            for i in range(num_split):
                split_var = deepcopy(variant)
                split_var['familyGuids'] = variant['familyGuids'][i*MAX_FAMILIES_PER_ROW:(i+1)*MAX_FAMILIES_PER_ROW]
                split_gen = set(gen_keys[i*gens_per_row:(i+1)*gens_per_row])
                split_var['genotypes'] = {k: v for k, v in variant['genotypes'].items() if k in split_gen}
                split_variants.append(split_var)

        variants = split_variants

    max_families_per_variant = max([len(variant.get('familyGuids', [1])) for variant in variants])
    max_samples_per_variant = max([len(variant.get('genotypes', {})) for variant in variants])

    rows = []
    for variant in variants:
        row = [_get_field_value(variant, config) for config in VARIANT_EXPORT_DATA]

        family_saved_variants = saved_variants_by_variant_family.get(variant['variantId'], {})
        for family_guid in variant.get('familyGuids', []):
            variant_guid = family_saved_variants.get(family_guid, '')
            family_tags = {
                'family_id': family_ids_by_guid.get(family_guid),
                'tags': [tag for tag in json_saved_variants['variantTagsByGuid'].values() if variant_guid in tag['variantGuids']],
                'notes': [note for note in json_saved_variants['variantNotesByGuid'].values() if variant_guid in note['variantGuids']],
            }
            row += [_get_field_value(family_tags, config) for config in VARIANT_FAMILY_EXPORT_DATA]
        num_blank_cols = len(VARIANT_FAMILY_EXPORT_DATA) * (max_families_per_variant - len(variant.get('familyGuids', [])))
        if 'familyGuids' not in variant:
            row.append(f"{variant['numFamilies']} Families")
            num_blank_cols -= 1
        row += ['' for i in range(num_blank_cols)]

        genotypes = [genotype for _, genotype in sorted(variant.get('genotypes', {}).items())]
        for genotype in genotypes:
            row += [_get_field_value(genotype, config) for config in VARIANT_SAMPLE_DATA]
        row += ['' for i in range(len(VARIANT_SAMPLE_DATA) * (max_samples_per_variant - len(genotypes)))]
        rows.append(row)

    header = [config['header'] for config in VARIANT_EXPORT_DATA]
    for i in range(max_families_per_variant):
        header += ['{}_{}'.format(config['header'], i+1) for config in VARIANT_FAMILY_EXPORT_DATA]
    for i in range(max_samples_per_variant):
        header += ['{}_{}'.format(config['header'], i+1) for config in VARIANT_SAMPLE_DATA]

    file_format = request.GET.get('file_format', 'tsv')

    return export_table('search_results_{}'.format(search_hash), header, rows, file_format, titlecase_header=False)


def _get_field_value(value, config):
    field_value = jmespath.search(config.get('value_path', config['header']), value)
    if config.get('process'):
        field_value = config['process'](field_value)
    return field_value


@login_and_policies_required
def search_context_handler(request):
    """Search variants.
    """
    response = _get_saved_searches(request.user)
    context = json.loads(request.body)

    projects = None
    if context.get('projectGuid'):
        projects = Project.objects.filter(guid=context.get('projectGuid'))
    elif context.get('familyGuid'):
        projects = Project.objects.filter(family__guid=context.get('familyGuid'))
    elif context.get('analysisGroupGuid'):
        projects = Project.objects.filter(analysisgroup__guid=context.get('analysisGroupGuid'))
    elif context.get('projectCategoryGuid'):
        projects = Project.objects.filter(projectcategory__guid=context.get('projectCategoryGuid'))
    elif context.get('searchHash'):
        search_context = context.get('searchParams')
        try:
            results_model = _get_or_create_results_model(context['searchHash'], search_context, request.user)
        except Exception as e:
            return create_json_response({'error': str(e)}, status=400, reason=str(e))
        projects = Project.objects.filter(family__in=results_model.families.all()).distinct()

    if not projects:
        error = 'Invalid context params: {}'.format(json.dumps(context))
        return create_json_response({'error': error}, status=400, reason=error)

    check_projects_view_permission(projects, request.user)

    project_guid = projects[0].guid if len(projects) == 1 else None
    response.update(get_projects_child_entities(projects, project_guid, request.user))

    response['familiesByGuid'] = {f['familyGuid']: f for f in Family.objects.filter(project__in=projects).values(
        projectGuid=Value(project_guid) if project_guid else F('project__guid'),
        familyGuid=F('guid'),
        analysisStatus=F('analysis_status'),
        **FAMILY_ADDITIONAL_VALUES,
    )}

    family_sample_types = Sample.objects.filter(individual__family__project__in=projects, is_active=True).values('individual__family__guid').annotate(
        samples=ArrayAgg(JSONObject(sampleType='sample_type', datasetType='dataset_type', isActive=Value(True)), distinct=True))
    project_dataset_types = defaultdict(set)
    for agg in family_sample_types:
        family = response['familiesByGuid'][agg['individual__family__guid']]
        family['sampleTypes'] = agg['samples']
        project_dataset_types[family['projectGuid']].update([s['datasetType'] for s in agg['samples']])
    for project_guid, dataset_types in project_dataset_types.items():
        response['projectsByGuid'][project_guid]['datasetTypes'] = list(dataset_types)

    project_category_guid = context.get('projectCategoryGuid')
    if project_category_guid:
        response['projectCategoriesByGuid'] = {
            project_category_guid: ProjectCategory.objects.get(guid=project_category_guid).json()
        }

    return create_json_response(response)


@login_and_policies_required
def get_saved_search_handler(request):
    return create_json_response(_get_saved_searches(request.user))


@login_and_policies_required
def create_saved_search_handler(request):
    request_json = json.loads(request.body)
    name = request_json.pop('name', None)
    if not name:
        error = '"Name" is required'
        return create_json_response({'error': error}, status=400, reason=error)

    if (request_json.get('inheritance') or {}).get('filter', {}).get('genotype'):
        error = 'Saved searches cannot include custom genotype filters'
        return create_json_response({'error': error}, status=400, reason=error)

    try:
        saved_search, _ = get_or_create_model_from_json(
            VariantSearch, {'search': request_json, 'created_by': request.user}, {'name': name}, request.user)
    except MultipleObjectsReturned:
        # Can't create a unique constraint on JSON field, so its possible that a duplicate gets made by accident
        dup_searches = VariantSearch.objects.filter(
            search=request_json,
            created_by=request.user,
        ).order_by('created_date')
        saved_search = dup_searches.first()
        VariantSearch.bulk_delete(request.user, queryset=dup_searches.exclude(guid=saved_search.guid))
        update_model_from_json(saved_search, {'name': name}, request.user)
    except IntegrityError:
        error = 'Saved search with name "{}" already exists'.format(name)
        return create_json_response({'error': error}, status=400, reason=error)

    return create_json_response({
        'savedSearchesByGuid': {
            saved_search.guid: get_json_for_saved_search(saved_search, request.user)
        }
    })


@login_and_policies_required
def update_saved_search_handler(request, saved_search_guid):
    search = VariantSearch.objects.get(guid=saved_search_guid)
    check_user_created_object_permissions(search, request.user)

    request_json = json.loads(request.body)
    name = request_json.pop('name', None)
    if not name:
        return create_json_response({}, status=400, reason='"Name" is required')

    update_model_from_json(search, {'name': name}, request.user)

    return create_json_response({
        'savedSearchesByGuid': {
            saved_search_guid: get_json_for_saved_search(search, request.user)
        }
    })


@login_and_policies_required
def delete_saved_search_handler(request, saved_search_guid):
    search = VariantSearch.objects.get(guid=saved_search_guid)
    search.delete_model(request.user)
    return create_json_response({'savedSearchesByGuid': {saved_search_guid: None}})


def _check_results_permission(results_model, user, project_perm_check=None):
    projects = Project.objects.filter(family__variantsearchresults=results_model)
    check_projects_view_permission(projects, user)
    if project_perm_check:
        for project in projects:
            if not project_perm_check(project):
                raise PermissionDenied()
    return projects


def _get_search_context(results_model):
    project_families = defaultdict(list)
    for family_guid, project_guid in results_model.families.values_list('guid', 'project__guid').order_by('guid'):
        project_families[project_guid].append(family_guid)

    return {
        'search': results_model.variant_search.search,
        'projectFamilies': [
            {'projectGuid': project_guid, 'familyGuids': family_guids}
            for project_guid, family_guids in project_families.items()
        ],
    }


def _get_saved_searches(user):
    saved_search_models = VariantSearch.objects.filter(
        Q(name__isnull=False),
        Q(created_by=user) | Q(created_by__isnull=True)
    )
    saved_searches = get_json_for_saved_searches(saved_search_models, user)
    return {'savedSearchesByGuid': {search['savedSearchGuid']: search for search in saved_searches}}


def _get_saved_variant_models(variants):
    variant_qs = []
    variant_ids_by_family = defaultdict(set)
    for variant in variants:
        for family_guid in variant.get('familyGuids', []):
            variant_ids_by_family[family_guid].add(variant['variantId'])

    for family_guid, variant_ids in variant_ids_by_family.items():
        variant_qs.append(Q(variant_id__in=variant_ids, family__guid=family_guid))

    if variant_qs:
        variant_q = variant_qs[0]
        for q in variant_qs[1:]:
            variant_q |= q
        saved_variants = SavedVariant.objects.filter(variant_q)
    else:
        saved_variants = SavedVariant.objects.none()

    return saved_variants

def _flatten_variants(variants):
    flattened_variants = []
    for variant in variants:
        if isinstance(variant, list):
            for compound_het in variant:
                flattened_variants.append(compound_het)
        else:
            flattened_variants.append(variant)
    return flattened_variants


@login_and_policies_required
def variant_lookup_handler(request):
    variant_id = request.GET.get('variantId')
    genome_version = request.GET.get('genomeVersion') or GENOME_VERSION_GRCh38
    bool_kwargs = {_to_snake_case(field): bool(request.GET.get(field)) for field in ['affectedOnly', 'homOnly']}
    variants = _get_variants_with_cache(
        _get_lookup_cache_key, clickhouse_variant_lookup,
        request.user, variant_id, sample_type=request.GET.get('sampleType'), genome_version=genome_version, **bool_kwargs,
    )

    family_guids = set()
    for variant in variants:
        family_guids.update(variant['familyGenotypes'].keys())

    families = Family.objects.filter(
        guid__in=family_guids,
        project__guid__in=get_project_guids_user_can_view(request.user, limit_data_manager=True),
    )
    for variant in variants:
        variant['familyGuids'] = list(families.values_list('guid', flat=True))

    saved_variants = _get_saved_variant_models(variants) if families else None
    response = get_variants_response(
        request, saved_variants=saved_variants, response_variants=variants,
        add_all_context=True, add_locus_list_detail=True, genome_version=genome_version,
    )

    individual_guid_map = {
        (i['familyGuid'], i['individualId']): i['individualGuid'] for i in response['individualsByGuid'].values()
    }
    for variant in variants:
        _update_lookup_variant(variant, response, individual_guid_map, request.user)

    return create_json_response(response)


def _get_lookup_cache_key(user, variant_id, sample_type, genome_version, affected_only, hom_only):
    cache_fields = ['variant_lookup_results', variant_id, genome_version]
    if affected_only:
        cache_fields.append('affected')
    if hom_only:
        cache_fields.append('hom')
    return '__'.join(cache_fields)


def _update_lookup_variant(variant, response, individual_guid_map, user):
    no_access_families = set(variant['familyGenotypes']) - set(variant['familyGuids'])
    individual_summary_map = {
        (i.pop('family__guid'), i.pop('individual_id')): (i.pop('guid'), i)
        for i in Individual.objects.filter(family__guid__in=no_access_families).values(
            'family__guid', 'individual_id', 'affected', 'sex', 'features', 'guid',
            vlmContactEmail=F('family__project__vlm_contact_email'),
            restrict_sharing=F('family__project__restrict_sharing'),
        )
    }
    add_individual_hpo_details([i for _, i in individual_summary_map.values()])

    variant['genotypes'] = {}
    variant['lookupFamilyGuids'] = sorted([guid for guid in variant.pop('familyGuids') if guid in variant['familyGenotypes']])
    variant['familyGuids'] = []
    for family_guid in variant['lookupFamilyGuids']:
        for genotype in variant['familyGenotypes'].pop(family_guid):
            individual_guid = individual_guid_map.get((family_guid, genotype['sampleId']))
            if not individual_guid:
                logger.error(
                    f'Unable to map sample {genotype["sampleId"]} in family {family_guid} to an individual for variant {variant["variantId"]}',
                    user,
                )
                continue
            genotype = {**genotype, 'individualGuid': individual_guid}
            if individual_guid in variant['genotypes']:
                genotype = [variant['genotypes'][individual_guid], genotype]
            variant['genotypes'][individual_guid] = genotype

    for i, (unmapped_family_guid, genotypes) in enumerate(sorted(variant.pop('familyGenotypes').items())):
        family_guid = f'F{i}_{variant["variantId"]}'
        variant['lookupFamilyGuids'].append(family_guid)
        if unmapped_family_guid in variant.get('liftedFamilyGuids', []):
            variant['liftedFamilyGuids'][variant['liftedFamilyGuids'].index(unmapped_family_guid)] = family_guid
        individual_guid_map = {}
        for j, genotype in enumerate(genotypes):
            unmapped_individual_guid, individual = individual_summary_map[(genotype.pop('familyGuid'), genotype.pop('sampleId'))]
            if unmapped_individual_guid in individual_guid_map:
                individual_guid = individual_guid_map[unmapped_individual_guid]
                variant['genotypes'][individual_guid] = [variant['genotypes'][individual_guid], genotype]
                continue
            individual_guid = f'I{j}_{family_guid}'
            individual_guid_map[unmapped_individual_guid] = individual_guid
            features = individual['features'] or []
            if individual.pop('restrict_sharing'):
                feature_category_count = defaultdict(int)
                for feature in features:
                    feature_category_count[feature.get('category', 'Other')] += 1
                features = [
                    {'category': category, 'label': f'{count} terms'}
                    for category, count in feature_category_count.items()
                ]
            response['individualsByGuid'][individual_guid] = {
                **individual,
                'familyGuid': family_guid,
                'individualGuid': individual_guid,
                'features': features,
            }
            variant['genotypes'][individual_guid] = genotype


@login_and_policies_required
def vlm_lookup_handler(request):
    kwargs = {_to_snake_case(k): v for k, v in request.GET.items()}
    variant_id = kwargs.pop('variant_id')
    parsed_variant_id = parse_variant_id(variant_id)
    if not parsed_variant_id:
        raise InvalidSearchException('VLM lookup is not supported for SVs')
    invalid_alleles = [f'"{allele}"' for allele in parsed_variant_id[2:] if not re.fullmatch(r'[ATCG]+', allele)]
    if invalid_alleles:
        raise InvalidSearchException(f'Unable to search VLM for invalid allele(s): {", ".join(invalid_alleles)}')
    if any(len(allele) > 1 for allele in parsed_variant_id[2:]):
        raise InvalidSearchException('VLM lookup is not supported for InDels')

    return create_json_response({'vlmMatches': vlm_lookup(request.user, *parsed_variant_id, **kwargs)})

def search_results_redirect(request):
    return redirect(request.get_full_path().replace('/report/custom_search', '/variant_search/results'), permanent=True)
