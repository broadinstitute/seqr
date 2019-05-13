import json
import jmespath
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Q, prefetch_related_objects
from django.views.decorators.csrf import csrf_exempt
from elasticsearch.exceptions import ConnectionTimeout

from seqr.models import Project, Family, Individual, SavedVariant, VariantSearch, VariantSearchResults
from seqr.utils.es_utils import get_es_variants, get_single_es_variant, InvalidIndexException, XPOS_SORT_KEY, \
    PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.saved_variant_api import _saved_variant_genes, _add_locus_lists
from seqr.views.pages.project_page import get_project_variant_tag_types, get_project_child_entities
from seqr.views.utils.export_table_utils import export_table
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import \
    get_json_for_variant_functional_data_tag_types, \
    _get_json_for_project, \
    get_json_for_saved_variants, \
    get_json_for_saved_search,\
    get_json_for_saved_searches
from seqr.views.utils.permissions_utils import check_permissions


GENOTYPE_AC_LOOKUP = {
    'ref_ref': [0, 0],
    'has_ref': [0, 1],
    'ref_alt': [1, 1],
    'has_alt': [1, 2],
    'alt_alt': [2, 2],
}
AFFECTED = Individual.AFFECTED_STATUS_AFFECTED
UNAFFECTED = Individual.AFFECTED_STATUS_UNAFFECTED


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def query_variants_handler(request, search_hash):
    """Search variants.
    """
    page = int(request.GET.get('page') or 1)
    per_page = int(request.GET.get('per_page') or 100)
    sort = request.GET.get('sort') or XPOS_SORT_KEY
    if sort == PATHOGENICTY_SORT_KEY and request.user.is_staff:
        sort = PATHOGENICTY_HGMD_SORT_KEY

    results_model = VariantSearchResults.objects.filter(search_hash=search_hash).first()
    if not results_model:
        if not request.body:
            return create_json_response({}, status=400, reason='Invalid search hash: {}'.format(search_hash))

        search_context = json.loads(request.body)

        project_families = search_context.get('projectFamilies')
        if not project_families:
            return create_json_response({}, status=400, reason='Invalid search: no projects/ families specified')

        search_dict = search_context.get('search', {})
        search_model = VariantSearch.objects.filter(search=search_dict).filter(Q(created_by=request.user) | Q(name__isnull=False)).first()
        if not search_model:
            search_model = VariantSearch.objects.create(created_by=request.user, search=search_dict)

        results_model = VariantSearchResults.objects.create(search_hash=search_hash, variant_search=search_model)

        all_families = set()
        for project_family in project_families:
            all_families.update(project_family['familyGuids'])
        results_model.families.set(Family.objects.filter(guid__in=all_families))

    _check_results_permission(results_model, request.user)

    try:
        variants, total_results = get_es_variants(results_model, sort=sort, page=page, num_results=per_page)
    except InvalidIndexException as e:
        return create_json_response({}, status=400, reason=e.message)
    except ConnectionTimeout as e:
        return create_json_response({}, status=504, reason='Query Time Out')

    response = _process_variants(variants, results_model.families.all())
    response['search'] = _get_search_context(results_model)
    response['search']['totalResults'] = total_results

    return create_json_response(response)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def query_single_variant_handler(request, variant_id):
    """Search variants.
    """
    families = Family.objects.filter(guid=request.GET.get('familyGuid'))

    variant = get_single_es_variant(families, variant_id)

    response = _process_variants([variant], families)
    response.update(_get_project_details(families.first().project, request.user))

    return create_json_response(response)


def _process_variants(variants, families):
    prefetch_related_objects(families, 'project')
    genes = _saved_variant_genes(variants)
    # TODO add locus lists on the client side (?)
    projects = {family.project for family in families}
    _add_locus_lists(projects, variants, genes)
    saved_variants_by_guid = _get_saved_variants(variants)

    return {
        'searchedVariants': variants,
        'savedVariantsByGuid': saved_variants_by_guid,
        'genesById': genes,
    }


PREDICTION_MAP = {
    'D': 'damaging',
    'T': 'tolerated',
}

POLYPHEN_MAP = {
    'D': 'probably_damaging',
    'P': 'possibly_damaging',
    'B': 'benign',
}

MUTTASTR_MAP = {
    'A': 'disease_causing',
    'D': 'disease_causing',
    'N': 'polymorphism',
    'P': 'polymorphism',
}

def _get_prediction_val(prediction):
    return PREDICTION_MAP.get(prediction[0]) if prediction else None

VARIANT_EXPORT_DATA = [
    {'header': 'chrom'},
    {'header': 'pos'},
    {'header': 'ref'},
    {'header': 'alt'},
    {'header': 'gene', 'value_path': 'mainTranscript.geneSymbol'},
    {'header': 'worst_consequence', 'value_path': 'mainTranscript.majorConsequence'},
    {'header': '1kg_freq', 'value_path': 'populations.g1k.af'},
    {'header': 'exac_freq', 'value_path': 'populations.exac.af'},
    {'header': 'gnomad_genomes_freq', 'value_path': 'populations.gnomad_genomes.af'},
    {'header': 'gnomad_exomes_freq', 'value_path': 'populations.gnomad_exomes.af'},
    {'header': 'topmed_freq', 'value_path': 'populations.topmed.af'},
    {'header': 'cadd', 'value_path': 'predictions.cadd'},
    {'header': 'revel', 'value_path': 'predictions.revel'},
    {'header': 'eigen', 'value_path': 'predictions.eigen'},
    {'header': 'polyphen', 'value_path': 'predictions.polyphen', 'process': lambda prediction: POLYPHEN_MAP.get(prediction[0]) if prediction else None},
    {'header': 'sift', 'value_path': 'predictions.sift', 'process': lambda prediction: PREDICTION_MAP.get(prediction[0]) if prediction else None},
    {'header': 'muttaster', 'value_path': 'predictions.mut_taster', 'process': lambda prediction: MUTTASTR_MAP.get(prediction[0]) if prediction else None},
    {'header': 'fathmm', 'value_path': 'predictions.fathmm', 'process': lambda prediction: PREDICTION_MAP.get(prediction[0]) if prediction else None},
    {'header': 'rsid', 'value_path': 'rsid'},
    {'header': 'hgvsc', 'value_path': 'mainTranscript.hgvsc'},
    {'header': 'hgvsp', 'value_path': 'mainTranscript.hgvsp'},
    {'header': 'clinvar_clinical_significance', 'value_path': 'clinvar.clinicalSignificance'},
    {'header': 'clinvar_gold_stars', 'value_path': 'clinvar.goldStars'},
    {'header': 'filter', 'value_path': 'genotypeFilters'},
]

VARIANT_FAMILY_EXPORT_DATA = [
    {'header': 'family_id'},
    {'header': 'tags', 'process': lambda tags: '|'.join(['{} ({})'.format(tag['name'], tag['createdBy']) for tag in tags or []])},
    {'header': 'notes', 'process': lambda notes: '|'.join(['{} ({})'.format(note['note'], note['createdBy']) for note in notes or []])},
]

VARIANT_GENOTYPE_EXPORT_DATA = [
    {'header': 'sample_id', 'value_path': 'sampleId'},
    {'header': 'num_alt_alleles', 'value_path': 'numAlt'},
    {'header': 'ad'},
    {'header': 'dp'},
    {'header': 'gq'},
    {'header': 'ab'},
]


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def export_variants_handler(request, search_hash):
    results_model = VariantSearchResults.objects.get(search_hash=search_hash)

    _check_results_permission(results_model, request.user)

    family_ids_by_guid = {family.guid: family.family_id for family in results_model.families.all()}

    variants, _ = get_es_variants(results_model, page=1, load_all=True)

    saved_variants_by_guid = _get_saved_variants(variants)
    saved_variants_by_family = defaultdict(dict)
    for var in saved_variants_by_guid.values():
        for family_guid in var['familyGuids']:
            saved_variants_by_family[family_guid]['{}-{}-{}'.format(var['xpos'], var['ref'], var['alt'])] = var

    max_families_per_variant = max([len(variant['familyGuids']) for variant in variants])
    max_samples_per_variant = max([len(variant['genotypes']) for variant in variants])

    rows = []
    for variant in variants:
        row = [_get_field_value(variant, config) for config in VARIANT_EXPORT_DATA]
        for i in range(max_families_per_variant):
            family_guid = variant['familyGuids'][i] if i < len(variant['familyGuids']) else ''
            family_tags = saved_variants_by_family[family_guid].get('{}-{}-{}'.format(variant['xpos'], variant['ref'], variant['alt'])) or {}
            family_tags['family_id'] = family_ids_by_guid.get(family_guid)
            row += [_get_field_value(family_tags, config) for config in VARIANT_FAMILY_EXPORT_DATA]
        genotypes = variant['genotypes'].values()
        for i in range(max_samples_per_variant):
            genotype = genotypes[i] if i < len(genotypes) else {}
            row += [_get_field_value(genotype, config) for config in VARIANT_GENOTYPE_EXPORT_DATA]
        rows.append(row)

    header = [config['header'] for config in VARIANT_EXPORT_DATA]
    for i in range(max_families_per_variant):
        header += ['{}_{}'.format(config['header'], i+1) for config in VARIANT_FAMILY_EXPORT_DATA]
    for i in range(max_samples_per_variant):
        header += ['{}_{}'.format(config['header'], i+1) for config in VARIANT_GENOTYPE_EXPORT_DATA]

    file_format = request.GET.get('file_format', 'tsv')

    return export_table('search_results_{}'.format(search_hash), header, rows, file_format, titlecase_header=False)


def _get_field_value(value, config):
    field_value = jmespath.search(config.get('value_path', config['header']), value)
    if config.get('process'):
        field_value = config['process'](field_value)
    return field_value


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def search_context_handler(request):
    """Search variants.
    """
    response = _get_saved_searches(request.user)
    project_guid = request.GET.get('projectGuid')

    if project_guid:
        project = Project.objects.get(guid=project_guid)
    elif request.GET.get('familyGuid'):
        project = Project.objects.get(family__guid=request.GET.get('familyGuid'))
    elif request.GET.get('analysisGroupGuid'):
        project = Project.objects.get(analysisgroup__guid=request.GET.get('analysisGroupGuid'))
    else:
        return create_json_response({}, status=400, reason='Invalid query params: {}'.format(json.dumps(request.GET)))

    response.update(_get_project_details(project, request.user))

    return create_json_response(response)


def _get_project_details(project, user):
    check_permissions(project, user)

    project_json = _get_json_for_project(project, user)

    families_by_guid, individuals_by_guid, samples_by_guid, analysis_groups_by_guid, locus_lists_by_guid = get_project_child_entities(project, user)

    project_json.update({
        'hasGeneSearch': True,
        'locusListGuids': locus_lists_by_guid.keys(),
        'variantTagTypes': get_project_variant_tag_types(project),
        'variantFunctionalTagTypes': get_json_for_variant_functional_data_tag_types(),
    })

    return {
        'projectsByGuid': {project.guid: project_json},
        'familiesByGuid': families_by_guid,
        'individualsByGuid': individuals_by_guid,
        'samplesByGuid': samples_by_guid,
        'locusListsByGuid': locus_lists_by_guid,
        'analysisGroupsByGuid': analysis_groups_by_guid,
    }


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def get_saved_search_handler(request):
    return create_json_response(_get_saved_searches(request.user))


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_saved_search_handler(request):
    request_json = json.loads(request.body)
    name = request_json.pop('name', None)
    if not name:
        return create_json_response({}, status=400, reason='"Name" is required')

    if request_json.get('inheritance', {}).get('filter', {}).get('genotype'):
        return create_json_response({}, status=400, reason='Saved searches cannot include custom genotype filters')

    try:
        saved_search, _ = VariantSearch.objects.get_or_create(
            search=request_json,
            created_by=request.user,
        )
    except MultipleObjectsReturned:
        # Can't create a unique constraint on JSON field, so its possible that a duplicate gets made by accident
        dup_searches = VariantSearch.objects.filter(
            search=request_json,
            created_by=request.user,
        )
        saved_search = dup_searches[0]
        for search in dup_searches:
            search.delete()
    saved_search.name = name
    saved_search.save()

    return create_json_response({
        'savedSearchesByGuid': {
            saved_search.guid: get_json_for_saved_search(saved_search, request.user)
        }
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_saved_search_handler(request, saved_search_guid):
    search = VariantSearch.objects.get(guid=saved_search_guid)
    if search.created_by != request.user:
        return create_json_response({}, status=403, reason='User does not have permission to edit this search')

    request_json = json.loads(request.body)
    name = request_json.pop('name', None)
    if not name:
        return create_json_response({}, status=400, reason='"Name" is required')

    search.name = name
    search.save()

    return create_json_response({
        'savedSearchesByGuid': {
            saved_search_guid: get_json_for_saved_search(search, request.user)
        }
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_saved_search_handler(request, saved_search_guid):
    search = VariantSearch.objects.get(guid=saved_search_guid)
    if search.created_by != request.user:
        return create_json_response({}, status=403, reason='User does not have permission to delete this search')

    search.delete()
    return create_json_response({'savedSearchesByGuid': {saved_search_guid: None}})


def _check_results_permission(results_model, user):
    families = results_model.families.prefetch_related('project').all()
    projects = {family.project for family in families}
    for project in projects:
        check_permissions(project, user)


def _get_search_context(results_model):
    project_families = defaultdict(list)
    for family in results_model.families.prefetch_related('project').all():
        project_families[family.project.guid].append(family.guid)

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


def _get_saved_variants(variants):
    if not variants:
        return {}

    variant_q = Q()
    for variant in variants:
        variant_q |= Q(xpos_start=variant['xpos'], ref=variant['ref'], alt=variant['alt'], family__guid__in=variant['familyGuids'])
    saved_variants = SavedVariant.objects.filter(variant_q)

    variants_by_id = {'{}-{}-{}'.format(var['xpos'], var['ref'], var['alt']): var for var in variants}
    saved_variants_json = get_json_for_saved_variants(saved_variants, add_tags=True)
    saved_variants_by_guid = {}
    for saved_variant in saved_variants_json:
        family_guids = saved_variant['familyGuids']
        saved_variant.update(
            variants_by_id['{}-{}-{}'.format(saved_variant['xpos'], saved_variant['ref'], saved_variant['alt'])]
        )
        #  For saved variants only use family it was saved for, not all families in search
        saved_variant['familyGuids'] = family_guids
        saved_variants_by_guid[saved_variant['variantGuid']] = saved_variant

    return saved_variants_by_guid
