import json
import jmespath
from collections import defaultdict
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.exceptions import MultipleObjectsReturned
from django.db import IntegrityError
from django.db.models import Q, prefetch_related_objects
from django.views.decorators.csrf import csrf_exempt
from elasticsearch.exceptions import ConnectionTimeout

from reference_data.models import GENOME_VERSION_GRCh37
from seqr.models import Project, Family, Individual, SavedVariant, VariantSearch, VariantSearchResults, Sample,\
    AnalysisGroup, ProjectCategory, VariantTagType
from seqr.utils.es_utils import get_es_variants, get_single_es_variant, get_es_variant_gene_counts,\
    InvalidIndexException, XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY
from seqr.utils.xpos_utils import get_xpos
from seqr.views.apis.saved_variant_api import _saved_variant_genes, _add_locus_lists
from seqr.views.utils.export_table_utils import export_table
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import \
    get_json_for_variant_functional_data_tag_types, \
    get_json_for_projects, \
    _get_json_for_families, \
    _get_json_for_individuals, \
    get_json_for_analysis_groups, \
    get_json_for_samples, \
    get_json_for_locus_lists, \
    get_json_for_saved_variants_with_tags, \
    get_json_for_saved_search,\
    get_json_for_saved_searches, \
    get_project_locus_list_models, \
    _get_json_for_models
from seqr.views.utils.permissions_utils import check_permissions, get_projects_user_can_view
from settings import API_LOGIN_REQUIRED_URL


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

    try:
        results_model = _get_or_create_results_model(search_hash, json.loads(request.body or '{}'), request.user)
    except Exception as e:
        return create_json_response({'error': e.message}, status=400, reason=e.message)

    _check_results_permission(results_model, request.user)

    try:
        variants, total_results = get_es_variants(results_model, sort=sort, page=page, num_results=per_page)
    except InvalidIndexException as e:
        return create_json_response({'error': e.message}, status=400, reason=e.message)
    except ConnectionTimeout as e:
        return create_json_response({}, status=504, reason='Query Time Out')

    response = _process_variants(variants or [], results_model.families.all())
    response['search'] = _get_search_context(results_model)
    response['search']['totalResults'] = total_results

    return create_json_response(response)


def _get_or_create_results_model(search_hash, search_context, user):
    results_model = VariantSearchResults.objects.filter(search_hash=search_hash).first()
    if not results_model:
        if not search_context:
            raise Exception('Invalid search hash: {}'.format(search_hash))

        project_families = search_context.get('projectFamilies')
        if project_families:
            all_families = set()
            for project_family in project_families:
                all_families.update(project_family['familyGuids'])
            families = Family.objects.filter(guid__in=all_families)
        elif search_context.get('allProjectFamilies'):
            omit_projects = ProjectCategory.objects.get(name='Demo').projects.all()
            projects = [project for project in get_projects_user_can_view(user) if project not in omit_projects]
            families = Family.objects.filter(project__in=projects)
        else:
            raise Exception('Invalid search: no projects/ families specified')

        search_dict = search_context.get('search', {})
        search_model = VariantSearch.objects.filter(search=search_dict).filter(
            Q(created_by=user) | Q(name__isnull=False)).first()
        if not search_model:
            search_model = VariantSearch.objects.create(created_by=user, search=search_dict)

        try:
            results_model = VariantSearchResults.objects.create(search_hash=search_hash, variant_search=search_model)
        except IntegrityError:
            # This can happen if a search_context request and results request are dispatched at the same time,
            results_model = VariantSearchResults.objects.get(search_hash=search_hash)
            try:
                results_model.families.set(families)
            except IntegrityError:
                pass
            return results_model

        results_model.families.set(families)
    return results_model


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def query_single_variant_handler(request, variant_id):
    """Search variants.
    """
    families = Family.objects.filter(guid=request.GET.get('familyGuid'))

    variant = get_single_es_variant(families, variant_id)

    response = _process_variants([variant], families)
    response.update(_get_projects_details([families.first().project], request.user))

    return create_json_response(response)


def _process_variants(variants, families):
    prefetch_related_objects(families, 'project')
    genes = _saved_variant_genes(variants)
    # TODO add locus lists on the client side (?)
    projects = {family.project for family in families}
    _add_locus_lists(projects, variants, genes)
    response_json, _ = _get_saved_variants(variants, families)

    response_json.update({
        'searchedVariants': variants,
        'genesById': genes,
    })
    return response_json


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


def _get_variant_main_transcript_field_val(parsed_variant):
    return next(
        (t for t in parsed_variant['transcripts'] if t['transcriptId'] == parsed_variant['mainTranscriptId']), {}
    ).get('value')


VARIANT_EXPORT_DATA = [
    {'header': 'chrom'},
    {'header': 'pos'},
    {'header': 'ref'},
    {'header': 'alt'},
    {'header': 'gene', 'value_path': '{transcripts: transcripts.*[].{value: geneSymbol, transcriptId: transcriptId}, mainTranscriptId: mainTranscriptId}', 'process': _get_variant_main_transcript_field_val},
    {'header': 'worst_consequence', 'value_path': '{transcripts: transcripts.*[].{value: majorConsequence, transcriptId: transcriptId}, mainTranscriptId: mainTranscriptId}', 'process': _get_variant_main_transcript_field_val},
    {'header': '1kg_freq', 'value_path': 'populations.g1k.af'},
    {'header': 'exac_freq', 'value_path': 'populations.exac.af'},
    {'header': 'gnomad_genomes_freq', 'value_path': 'populations.gnomad_genomes.af'},
    {'header': 'gnomad_exomes_freq', 'value_path': 'populations.gnomad_exomes.af'},
    {'header': 'topmed_freq', 'value_path': 'populations.topmed.af'},
    {'header': 'cadd', 'value_path': 'predictions.cadd'},
    {'header': 'revel', 'value_path': 'predictions.revel'},
    {'header': 'eigen', 'value_path': 'predictions.eigen'},
    {'header': 'polyphen', 'value_path': 'predictions.polyphen', 'process': _get_prediction_val},
    {'header': 'sift', 'value_path': 'predictions.sift', 'process': _get_prediction_val},
    {'header': 'muttaster', 'value_path': 'predictions.mut_taster', 'process': _get_prediction_val},
    {'header': 'fathmm', 'value_path': 'predictions.fathmm', 'process': _get_prediction_val},
    {'header': 'rsid', 'value_path': 'rsid'},
    {'header': 'hgvsc', 'value_path': '{transcripts: transcripts.*[].{value: hgvsc, transcriptId: transcriptId}, mainTranscriptId: mainTranscriptId}', 'process': _get_variant_main_transcript_field_val},
    {'header': 'hgvsp', 'value_path': '{transcripts: transcripts.*[].{value: hgvsp, transcriptId: transcriptId}, mainTranscriptId: mainTranscriptId}', 'process': _get_variant_main_transcript_field_val},
    {'header': 'clinvar_clinical_significance', 'value_path': 'clinvar.clinicalSignificance'},
    {'header': 'clinvar_gold_stars', 'value_path': 'clinvar.goldStars'},
    {'header': 'filter', 'value_path': 'genotypeFilters'},
]

VARIANT_FAMILY_EXPORT_DATA = [
    {'header': 'family_id'},
    {'header': 'tags', 'process': lambda tags: '|'.join([
        '{} ({})'.format(tag['name'], tag['createdBy']) for tag in
        sorted(tags or [], key=lambda tag: tag['lastModifiedDate'] or timezone.now(), reverse=True)
    ])},
    {'header': 'notes', 'process': lambda notes: '|'.join([
        u'{} ({})'.format(note['note'].replace('\n', ' '), note['createdBy']) for note in
        sorted(notes or [], key=lambda note: note['lastModifiedDate'] or timezone.now(), reverse=True)
    ])},
]


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def get_variant_gene_breakdown(request, search_hash):
    results_model = VariantSearchResults.objects.get(search_hash=search_hash)
    _check_results_permission(results_model, request.user)

    gene_counts = get_es_variant_gene_counts(results_model)
    return create_json_response({
        'searchGeneBreakdown': {search_hash: gene_counts},
        'genesById': get_genes(gene_counts.keys(), add_omim=True, add_constraints=True),
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def export_variants_handler(request, search_hash):
    results_model = VariantSearchResults.objects.get(search_hash=search_hash)

    _check_results_permission(results_model, request.user)

    families = results_model.families.all()
    family_ids_by_guid = {family.guid: family.family_id for family in families}

    variants, _ = get_es_variants(results_model, page=1, load_all=True)
    variants = _flatten_variants(variants)

    json, variants_to_saved_variants = _get_saved_variants(variants, families)

    max_families_per_variant = max([len(variant['familyGuids']) for variant in variants])
    max_samples_per_variant = max([len(variant['genotypes']) for variant in variants])

    rows = []
    for variant in variants:
        row = [_get_field_value(variant, config) for config in VARIANT_EXPORT_DATA]
        for i in range(max_families_per_variant):
            family_guid = variant['familyGuids'][i] if i < len(variant['familyGuids']) else ''
            variant_guid = variants_to_saved_variants.get(variant['variantId'], {}).get(family_guid, '')
            family_tags = {
                'family_id': family_ids_by_guid.get(family_guid),
                'tags': [tag for tag in json['variantTagsByGuid'].values() if variant_guid in tag['variantGuids']],
                'notes': [note for note in json['variantNotesByGuid'].values() if variant_guid in note['variantGuids']],
            }
            row += [_get_field_value(family_tags, config) for config in VARIANT_FAMILY_EXPORT_DATA]
        genotypes = variant['genotypes'].values()
        for i in range(max_samples_per_variant):
            if i < len(genotypes):
                row.append('{sampleId}:{numAlt}:{gq}:{ab}'.format(**genotypes[i]))
            else:
                row.append('')
        rows.append(row)

    header = [config['header'] for config in VARIANT_EXPORT_DATA]
    for i in range(max_families_per_variant):
        header += ['{}_{}'.format(config['header'], i+1) for config in VARIANT_FAMILY_EXPORT_DATA]
    header += ['sample_{}:num_alt_alleles:gq:ab'.format(i+1) for i in range(max_samples_per_variant)]

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
    context = json.loads(request.body)

    if context.get('projectGuid'):
        projects = Project.objects.filter(guid=context.get('projectGuid'))
    elif context.get('familyGuid'):
        projects = Project.objects.filter(family__guid=context.get('familyGuid'))
    elif context.get('analysisGroupGuid'):
        projects = Project.objects.filter(analysisgroup__guid=context.get('analysisGroupGuid'))
    elif context.get('projectCategoryGuid'):
        projects = Project.objects.filter(projectcategory__guid=context.get('projectCategoryGuid'))
    elif context.get('searchHash'):
        try:
            results_model = _get_or_create_results_model(context['searchHash'], context.get('searchParams'), request.user)
        except Exception as e:
            return create_json_response({'error': e.message}, status=400, reason=e.message)
        projects = Project.objects.filter(family__in=results_model.families.all()).distinct()
    else:
        error = 'Invalid context params: {}'.format(json.dumps(context))
        return create_json_response({'error': error}, status=400, reason=error)

    response.update(_get_projects_details(projects, request.user, project_category_guid=context.get('projectCategoryGuid')))

    return create_json_response(response)


def _get_projects_details(projects, user, project_category_guid=None):
    for project in projects:
        check_permissions(project, user)

    prefetch_related_objects(projects, 'can_view_group')
    project_models_by_guid = {project.guid: project for project in projects}
    projects_json = get_json_for_projects(projects, user)

    locus_lists = set()

    functional_data_tag_types = get_json_for_variant_functional_data_tag_types()
    variant_tag_types_by_guid = {
        vtt.guid: vtt for vtt in
        VariantTagType.objects.filter(Q(project__in=projects) | Q(project__isnull=True)).prefetch_related('project')
    }
    variant_tag_types = _get_json_for_models(variant_tag_types_by_guid.values())
    for project_json in projects_json:
        project = project_models_by_guid[project_json['projectGuid']]
        project_locus_lists = get_project_locus_list_models(project)
        locus_lists.update(project_locus_lists)

        project_json.update({
            'locusListGuids': [locus_list.guid for locus_list in project_locus_lists],
            'variantTagTypes': [
                vtt for vtt in variant_tag_types
                if variant_tag_types_by_guid[vtt['variantTagTypeGuid']].project is None or
                   variant_tag_types_by_guid[vtt['variantTagTypeGuid']].project.guid == project_json['projectGuid']],
            'variantFunctionalTagTypes': functional_data_tag_types,
        })

    families = _get_json_for_families(Family.objects.filter(project__in=projects), user)
    individuals = _get_json_for_individuals(Individual.objects.filter(family__project__in=projects), user=user)
    samples = get_json_for_samples(Sample.objects.filter(individual__family__project__in=projects))
    analysis_groups = get_json_for_analysis_groups(AnalysisGroup.objects.filter(project__in=projects))

    individual_guids_by_family = defaultdict(list)
    for individual in individuals:
        individual_guids_by_family[individual['familyGuid']].append(individual['individualGuid'])
    for family in families:
         family['individualGuids'] = individual_guids_by_family[family['familyGuid']]

    sample_guids_by_individual = defaultdict(list)
    for sample in samples:
        sample_guids_by_individual[sample['individualGuid']].append(sample['sampleGuid'])
    for individual in individuals:
        individual['sampleGuids'] = sample_guids_by_individual[individual['individualGuid']]

    response = {
        'projectsByGuid': {p['projectGuid']: p for p in projects_json},
        'familiesByGuid': {f['familyGuid']: f for f in families},
        'individualsByGuid': {i['individualGuid']: i for i in individuals},
        'samplesByGuid': {s['sampleGuid']: s for s in samples},
        'locusListsByGuid': {ll['locusListGuid']: ll for ll in get_json_for_locus_lists(list(locus_lists), user)},
        'analysisGroupsByGuid': {ag['analysisGroupGuid']: ag for ag in analysis_groups},
    }
    if project_category_guid:
        response['projectCategoriesByGuid'] = {
            project_category_guid: ProjectCategory.objects.get(guid=project_category_guid).json()
        }
    return response


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

    if (request_json.get('inheritance') or {}).get('filter', {}).get('genotype'):
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


def _get_saved_variants(variants, families):
    if not variants:
        return {}, {}

    variants = _flatten_variants(variants)

    prefetch_related_objects(families, 'project')
    hg37_family_guids = {family.guid for family in families if family.project.genome_version == GENOME_VERSION_GRCh37}

    variant_q = Q()
    variants_by_id = {}
    for variant in variants:
        variants_by_id[_get_variant_key(**variant)] = variant
        variant_q |= Q(xpos_start=variant['xpos'], ref=variant['ref'], alt=variant['alt'], family__guid__in=variant['familyGuids'])
        if variant['liftedOverGenomeVersion'] == GENOME_VERSION_GRCh37 and hg37_family_guids:
            variant_hg37_families = [family_guid for family_guid in variant['familyGuids'] if family_guid in hg37_family_guids]
            if variant_hg37_families:
                lifted_xpos = get_xpos(variant['liftedOverChrom'], variant['liftedOverPos'])
                variant_q |= Q(xpos_start=lifted_xpos, ref=variant['ref'], alt=variant['alt'], family__guid__in=variant_hg37_families)
                variants_by_id[_get_variant_key(
                    xpos=lifted_xpos, ref=variant['ref'], alt=variant['alt'], genomeVersion=variant['liftedOverGenomeVersion']
                )] = variant
    saved_variants = SavedVariant.objects.filter(variant_q)

    json = get_json_for_saved_variants_with_tags(saved_variants, add_details=True)
    variants_to_saved_variants = {}
    for saved_variant in json['savedVariantsByGuid'].values():
        family_guids = saved_variant['familyGuids']
        searched_variant = variants_by_id.get(_get_variant_key(**saved_variant))
        if not searched_variant:
            # This can occur when an hg38 family has a saved variant that did not successfully lift from hg37
            continue
        saved_variant.update(searched_variant)
        #  For saved variants only use family it was saved for, not all families in search
        saved_variant['familyGuids'] = family_guids
        json['savedVariantsByGuid'][saved_variant['variantGuid']] = saved_variant
        if searched_variant['variantId'] not in variants_to_saved_variants:
            variants_to_saved_variants[searched_variant['variantId']] = {}
        for family_guid in family_guids:
            variants_to_saved_variants[searched_variant['variantId']][family_guid] = saved_variant['variantGuid']

    return json, variants_to_saved_variants


def _get_variant_key(xpos=None, ref=None, alt=None, genomeVersion=None, **kwargs):
    return '{}-{}-{}_{}'.format(xpos, ref, alt, genomeVersion)


def _flatten_variants(variants):
    flattened_variants = []
    for variant in variants:
        if isinstance(variant, list):
            for compound_het in variant:
                flattened_variants.append(compound_het)
        else:
            flattened_variants.append(variant)
    return flattened_variants
