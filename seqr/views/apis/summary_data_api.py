from collections import defaultdict
from datetime import datetime
from django.core.exceptions import PermissionDenied
from django.db.models import CharField, F, Value, Case, When
from django.db.models.functions import Coalesce, Concat, JSONObject, NullIf
import json
from random import randint

from matchmaker.matchmaker_utils import get_mme_gene_phenotype_ids_for_submissions, parse_mme_features, \
    get_mme_metrics, get_hpo_terms_by_id
from matchmaker.models import MatchmakerSubmission
from reference_data.models import HumanPhenotypeOntology
from seqr.models import Project, Family, Individual, VariantTagType, SavedVariant, FamilyAnalysedBy
from seqr.views.utils.airtable_utils import AirtableSession
from seqr.views.utils.file_utils import load_uploaded_file
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_matchmaker_submissions, get_json_for_saved_variants,\
    add_individual_hpo_details, INDIVIDUAL_DISPLAY_NAME_EXPR
from seqr.views.utils.permissions_utils import analyst_required, user_is_analyst, get_project_guids_user_can_view, \
    login_and_policies_required, get_project_and_check_permissions, get_internal_projects
from seqr.views.utils.anvil_metadata_utils import parse_anvil_metadata, SHARED_DISCOVERY_TABLE_VARIANT_COLUMNS, \
    FAMILY_ROW_TYPE, DISCOVERY_ROW_TYPE
from seqr.views.utils.variant_utils import get_variants_response, get_discovery_phenotype_class, DISCOVERY_CATEGORY

MAX_SAVED_VARIANTS = 10000


@login_and_policies_required
def mme_details(request):
    submissions = MatchmakerSubmission.objects.filter(deleted_date__isnull=True).filter(
        individual__family__project__guid__in=get_project_guids_user_can_view(request.user))

    hpo_ids, gene_ids, submission_gene_variants = get_mme_gene_phenotype_ids_for_submissions(
        submissions, get_gene_variants=True)
    genes_by_id = get_genes(gene_ids)
    hpo_terms_by_id = get_hpo_terms_by_id(hpo_ids)

    submission_json = get_json_for_matchmaker_submissions(
        submissions, additional_model_fields=['label'], all_parent_guids=True)
    submissions_by_guid = {s['submissionGuid']: s for s in submission_json}

    for submission in submissions:
        gene_variants = submission_gene_variants[submission.guid]
        submissions_by_guid[submission.guid].update({
            'phenotypes': parse_mme_features(submission.features, hpo_terms_by_id),
            'geneVariants': gene_variants,
            'geneSymbols': ','.join({genes_by_id.get(gv['geneId'], {}).get('geneSymbol') for gv in gene_variants})
        })

    saved_variants = get_json_for_saved_variants(
        SavedVariant.objects.filter(matchmakersubmissiongenes__matchmaker_submission__guid__in=submissions_by_guid),
        add_details=True,
    )

    response = {
        'submissions': list(submissions_by_guid.values()),
        'genesById': genes_by_id,
        'savedVariantsByGuid': {s['variantGuid']: s for s in saved_variants},
    }
    if user_is_analyst(request.user):
        response['metrics'] = get_mme_metrics()

    return create_json_response(response)


@analyst_required
def success_story(request, success_story_types):
    if success_story_types == 'all':
        families = Family.objects.filter(success_story__isnull=False)
    else:
        success_story_types = success_story_types.split(',')
        families = Family.objects.filter(success_story_types__overlap=success_story_types)
    families = families.filter(project__guid__in=get_project_guids_user_can_view(request.user)).order_by('family_id')

    rows = [{
        "project_guid": family.project.guid,
        "family_guid": family.guid,
        "family_id": family.family_id,
        "success_story_types": family.success_story_types,
        "success_story": family.success_story,
        "row_id": family.guid,
    } for family in families]

    return create_json_response({
        'rows': rows,
    })


@login_and_policies_required
def saved_variants_page(request, tag):
    gene = request.GET.get('gene')
    if tag == 'ALL':
        saved_variant_models = SavedVariant.objects.exclude(varianttag=None)
    else:
        tags = tag.split(';')
        tag_types = VariantTagType.objects.filter(name__in=tags, project__isnull=True)
        saved_variant_models = SavedVariant.objects.filter(
            varianttag__variant_tag_type__category=DISCOVERY_CATEGORY, varianttag__variant_tag_type__project__isnull=True,
        ).distinct() if DISCOVERY_CATEGORY in tags else SavedVariant.objects.all()
        for tt in tag_types:
            saved_variant_models = saved_variant_models.filter(varianttag__variant_tag_type=tt).distinct()

    saved_variant_models = saved_variant_models.filter(family__project__guid__in=get_project_guids_user_can_view(request.user))

    if gene:
        saved_variant_models = saved_variant_models.filter(saved_variant_json__transcripts__has_key=gene)
    elif saved_variant_models.count() > MAX_SAVED_VARIANTS:
        return create_json_response({'error': 'Select a gene to filter variants'}, status=400)

    response_json = get_variants_response(
        request, saved_variant_models, add_all_context=True, include_igv=False, add_locus_list_detail=True,
        include_individual_gene_scores=False, include_project_name=True,
    )

    return create_json_response(response_json)


@login_and_policies_required
def hpo_summary_data(request, hpo_id):
    data = Individual.objects.filter(
        family__project__guid__in=get_project_guids_user_can_view(request.user),
        features__contains=[{'id': hpo_id}],
    ).order_by('id').values(
        'features', individualGuid=F('guid'), displayName=INDIVIDUAL_DISPLAY_NAME_EXPR, familyId=F('family__family_id'),
         familyData=JSONObject(
            projectGuid=F('family__project__guid'),
            genomeVersion=F('family__project__genome_version'),
            familyGuid=F('family__guid'),
            analysisStatus=F('family__analysis_status'),
            displayName=Coalesce(NullIf('family__display_name', Value('')), 'family__family_id'),
        ))
    add_individual_hpo_details(data)

    return create_json_response({'data': list(data)})


@analyst_required
def bulk_update_family_analysed_by(request):
    request_json = json.loads(request.body)
    data_type =request_json['dataType']
    family_upload_data = load_uploaded_file(request_json['familiesFile']['uploadedFileId'])
    header = [col.split()[0].lower() for col in family_upload_data[0]]
    if not ('project' in header and 'family' in header):
        return create_json_response({'error': 'Project and Family columns are required'}, status=400)
    requested_families = {(row[header.index('project')], row[header.index('family')]) for row in family_upload_data[1:]}

    family_db_id_lookup = {
        (f['project__name'], f['family_id']): f['id'] for f in Family.objects.annotate(
            project_family=Concat('project__name', 'family_id', output_field=CharField())
        ).filter(project_family__in=[f'{project}{family}' for project, family in requested_families])
        .values('id', 'family_id', 'project__name')
    }

    warnings = []
    missing_from_db = requested_families - set(family_db_id_lookup.keys())
    if missing_from_db:
        missing_families = ', '.join([f'{family} ({project})' for project, family in sorted(missing_from_db)])
        warnings.append(f'No match found for the following families: {missing_families}')

    analysed_by_models = [
        FamilyAnalysedBy(family_id=family_db_id_lookup[family_key], data_type=data_type, last_modified_date=datetime.now())
        for family_key in requested_families if family_key in family_db_id_lookup
    ]
    for ab in analysed_by_models:
        ab.guid = f'FAB{randint(10**5, 10**6)}_{ab}'[:FamilyAnalysedBy.MAX_GUID_SIZE] # nosec
    FamilyAnalysedBy.bulk_create(request.user, analysed_by_models)

    return create_json_response({
        'warnings': warnings,
        'info': [f'Updated "analysed by" for {len(analysed_by_models)} families'],
    })


ALL_PROJECTS = 'all'
GREGOR_CATEGORY = 'gregor'


def _get_metadata_projects(request, project_guid):
    is_analyst = user_is_analyst(request.user)
    is_all_projects = project_guid == ALL_PROJECTS
    include_airtable = 'true' in request.GET.get('includeAirtable', '') and is_analyst and not is_all_projects
    if is_all_projects:
        projects = get_internal_projects() if is_analyst else Project.objects.filter(
            guid__in=get_project_guids_user_can_view(request.user))
    elif project_guid == GREGOR_CATEGORY:
        if not is_analyst:
            raise PermissionDenied()
        projects = Project.objects.filter(projectcategory__name__iexact=GREGOR_CATEGORY)
    else:
        projects = [get_project_and_check_permissions(project_guid, request.user)]
    return projects, include_airtable


@login_and_policies_required
def sample_metadata_export(request, project_guid):
    projects, include_airtable = _get_metadata_projects(request, project_guid)

    family_rows_by_id = {}
    rows_by_subject_family_id = defaultdict(dict)
    collaborator_map = {}
    all_features = set()

    def _add_row(row, family_id, row_type):
        if row_type == FAMILY_ROW_TYPE:
            family_rows_by_id[family_id] = row
        elif row_type == DISCOVERY_ROW_TYPE:
            for i, discovery_row in enumerate(row):
                parsed_row = {
                    '{}-{}'.format(k, i + 1): discovery_row[k] for k in
                    SHARED_DISCOVERY_TABLE_VARIANT_COLUMNS + ['novel_mendelian_gene', 'phenotype_class'] if discovery_row.get(k)
                }
                parsed_row['num_saved_variants'] = len(row)
                rows_by_subject_family_id[(discovery_row['subject_id'], family_id)].update(parsed_row)
        else:
            row_key = (row['subject_id'], family_id)
            collaborator = row.pop('Collaborator', None)
            if collaborator:
                collaborator_map[row_key] = collaborator
            if 'ancestry_detail' in row:
                row['ancestry'] = row.pop('ancestry_detail')
            if 'hpo_present' in row:
                all_features.update(row['hpo_present'].split('|'))
                all_features.update(row['hpo_absent'].split('|'))
            rows_by_subject_family_id[row_key].update(row)

    parse_anvil_metadata(
        projects, request.GET.get('loadedBefore') or datetime.now().strftime('%Y-%m-%d'), request.user, _add_row,
        allow_missing_discovery_genes=True,
        omit_airtable=not include_airtable,
        get_additional_variant_fields=_get_additional_variant_fields,
        get_additional_sample_fields=lambda sample, airtable_metadata: {
            'data_type': sample.sample_type,
            'date_data_generation': sample.loaded_date.strftime('%Y-%m-%d'),
            'Collaborator': (airtable_metadata or {}).get('Collaborator'),
        }, family_values={
            'family_guid': F('guid'),
            'project_guid': F('project__guid'),
            'MME': Case(When(individual__matchmakersubmission__isnull=True, then=Value('N')), default=Value('Y')),
        },
    )

    if collaborator_map:
        collaborator_name_map = _get_airtable_collaborator_names(request.user, collaborator_map.values())
        for row_key, collaborator_id in collaborator_map.items():
            rows_by_subject_family_id[row_key]['sample_provider'] = collaborator_name_map.get(collaborator_id)

    hpo_name_map = {hpo.hpo_id: hpo.name for hpo in HumanPhenotypeOntology.objects.filter(hpo_id__in=all_features)}
    for row_key, row in rows_by_subject_family_id.items():
        row.update(family_rows_by_id[row_key[1]])
        row['num_saved_variants'] = row.get('num_saved_variants', 0)
        for hpo_key in ['hpo_present', 'hpo_absent']:
            if row[hpo_key]:
                row[hpo_key] = '|'.join(['{} ({})'.format(feature_id, hpo_name_map.get(feature_id, '')) for feature_id in row[hpo_key].split('|')])

    return create_json_response({'rows': list(rows_by_subject_family_id.values())})


def _get_additional_variant_fields(variant, *args):
    if 'discovery_tag_guids_by_name' not in variant:
        return {}
    discovery_tag_names = variant['discovery_tag_guids_by_name'].keys()
    is_novel = 'Y' if any('Novel gene' in name for name in discovery_tag_names) else 'N'
    return {
        'novel_mendelian_gene': is_novel,
        'phenotype_class': get_discovery_phenotype_class(discovery_tag_names),
    }


def _get_airtable_collaborator_names(user, collaborator_ids):
    collaborator_map = AirtableSession(user).fetch_records(
        'Collaborator', fields=['CollaboratorID'], or_filters={'RECORD_ID()': collaborator_ids}
    )
    return {
        collaborator_id: collaborator_map.get(collaborator_id, {}).get('CollaboratorID')
        for collaborator_id in collaborator_ids
    }
