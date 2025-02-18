"""
APIs for updating project metadata, as well as creating or deleting projects
"""

import json
from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max, Q, F, Value
from django.db.models.functions import JSONObject, TruncDate
from django.utils import timezone
from notifications.models import Notification

from matchmaker.models import MatchmakerSubmission
from seqr.models import Project, Family, Individual, Sample, RnaSample, FamilyNote, PhenotypePrioritization, CAN_EDIT
from seqr.views.utils.airtable_utils import AirtableSession, ANVIL_REQUEST_TRACKING_TABLE
from seqr.views.utils.individual_utils import delete_individuals
from seqr.views.utils.json_utils import create_json_response, _to_snake_case, _to_camel_case
from seqr.views.utils.json_to_orm_utils import update_project_from_json, create_model_from_json, update_model_from_json
from seqr.views.utils.orm_to_json_utils import _get_json_for_project, get_json_for_samples, \
    get_json_for_project_collaborator_list, get_json_for_matchmaker_submissions, \
    get_json_for_family_notes, _get_json_for_individuals, get_json_for_project_collaborator_groups, \
    FAMILY_ADDITIONAL_VALUES
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions, \
    check_user_created_object_permissions, pm_required, user_is_pm, login_and_policies_required, \
    has_workspace_perm, has_case_review_permissions, is_internal_anvil_project
from seqr.views.utils.project_context_utils import families_discovery_tags, \
    add_project_tag_type_counts, get_project_analysis_groups, get_project_locus_lists
from seqr.views.utils.terra_api_utils import is_anvil_authenticated, anvil_enabled
from settings import BASE_URL


@pm_required
def create_project_handler(request):
    """Create a new project.

    HTTP POST
        Request body - should contain json params:
            name: Project name
            description: Project description

        Response body - will be json with the following structure, representing the ,created project:
            {
                'projectsByGuid':  { <projectGuid1> : { ... <project key-value pairs> ... } }
            }

    """
    request_json = json.loads(request.body)

    required_fields = ['name', 'genomeVersion']
    has_anvil = is_anvil_authenticated(request.user)
    if has_anvil:
        required_fields += ['workspaceNamespace', 'workspaceName']

    missing_fields = [field for field in required_fields if not request_json.get(field)]
    if missing_fields:
        error = 'Field(s) "{}" are required'.format(', '.join(missing_fields))
        return create_json_response({'error': error}, status=400, reason=error)

    if has_anvil and not _is_valid_anvil_workspace(request_json, request.user):
        return create_json_response({'error': 'Invalid Workspace'}, status=400)

    project_args = {_to_snake_case(field): request_json[field] for field in required_fields}
    project_args.update({
        _to_snake_case(field): request_json.get(field, default) for field, default in
        [('description', ''), ('isDemo', False), ('consentCode', None)]
    })
    if request_json.get('disableMme'):
        project_args['is_mme_enabled'] = False

    project = create_model_from_json(Project, project_args, user=request.user)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


def _is_valid_anvil_workspace(request_json, user):
    namespace = request_json.get('workspaceNamespace')
    name = request_json.get('workspaceName')
    return bool(name and namespace and has_workspace_perm(user, CAN_EDIT, namespace, name))


@login_and_policies_required
def update_project_handler(request, project_guid):
    """Update project metadata - including one or more of these fields: name, description

    Args:
        project_guid (string): GUID of the project that should be updated

    HTTP POST
        Request body - should contain the following json structure:
        {
            'form' : {
                'name':  <project name>,
                'description': <project description>,
            }
        }

        Response body - will contain the following structure, representing the updated project:
            {
                'projectsByGuid':  {
                    <projectGuid1> : { ... <project key-value pairs> ... }
                }
            }

    """

    project = Project.objects.get(guid=project_guid)

    check_project_permissions(project, request.user, can_edit=True)

    request_json = json.loads(request.body)
    updated_fields = None
    consent_code = request_json.get('consentCode')
    if consent_code and consent_code != project.consent_code:
        if not user_is_pm(request.user):
            raise PermissionDenied('User is not authorized to edit consent code')
        project.consent_code = consent_code
        updated_fields = {'consent_code'}

    update_project_from_json(project, request_json, request.user, allow_unknown_keys=True, updated_fields=updated_fields)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@pm_required
def update_project_workspace(request, project_guid):
    if not is_anvil_authenticated(request.user):
        raise PermissionDenied()

    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)

    request_json = json.loads(request.body)
    if not _is_valid_anvil_workspace(request_json, request.user):
        return create_json_response({'error': 'Invalid Workspace'}, status=400)

    update_json = {k: request_json[k] for k in ['workspaceNamespace', 'workspaceName']}
    update_model_from_json(project, update_json, request.user)

    return create_json_response(_get_json_for_project(project, request.user))


@login_and_policies_required
def delete_project_handler(request, project_guid):
    """Delete project - request handler.

    Args:
        project_guid (string): GUID of the project to delete
    """

    _delete_project(project_guid, request.user)

    return create_json_response({
        'projectsByGuid': {
            project_guid: None
        },
    })


@login_and_policies_required
def project_page_data(request, project_guid):
    """
    Returns a JSON object containing basic project information

    Args:
        project_guid (string): GUID of the Project to retrieve data for.
    """
    project = get_project_and_check_permissions(project_guid, request.user)
    update_project_from_json(project, {'last_accessed_date': timezone.now()}, request.user)
    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user, add_project_category_guids_field=False)
        },
    })


FAMILY_INDIVIDUAL_FIELDS = {
    'caseReviewStatuses': {'agg': ArrayAgg('case_review_status', distinct=True, filter=~Q(case_review_status=''))},
    'caseReviewStatusLastModified': {'agg': Max('case_review_status_last_modified_date'), 'default': None},
    'parental_ids': {
        'agg': ArrayAgg(JSONObject(**{k: k for k in ['id', 'guid', 'father_id', 'mother_id']})),
        'format': lambda parental_ids, id_guid_map: [
            {'paternalGuid': id_guid_map.get(p['father_id']), 'maternalGuid': id_guid_map.get(p['mother_id']), 'individualGuid': p['guid']}
            for p in parental_ids if p['father_id'] or p['mother_id']
        ],
        'response_key': 'parents',
    },
    'metadata_count': {
        'agg': Count('id', filter=Q(
            features__0__isnull=False, birth_year__isnull=False,
            population__isnull=False, proband_relationship__isnull=False,
        )),
        'format': lambda metadata_count, *args: bool(metadata_count),
        'response_key': 'hasRequiredMetadata',
    },
}


def _get_formatted_value(value, config, *args):
    value = value or config.get('default', [])
    if config.get('format'):
        value = config['format'](value, *args)
    return value


@login_and_policies_required
def project_families(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    family_models = Family.objects.filter(project=project)
    families = family_models.values(
        'id', 'description',
        **{_to_camel_case(field): F(field) for field in [
            'family_id', 'analysis_status', 'created_date', 'coded_phenotype', 'mondo_id', 'external_data',
        ]},
        familyGuid=F('guid'),
        projectGuid=Value(project_guid),
        **FAMILY_ADDITIONAL_VALUES,
    )
    families_by_id = {f.pop('id'): f for f in families}

    has_data_families = {
        key: set(models.filter(
            individual__family_id__in=families_by_id).values_list('individual__family_id', flat=True).distinct()
        ) for key, models in [
            ('hasPhenotypePrioritization', PhenotypePrioritization.objects),
            ('hasRna', RnaSample.objects.filter(is_active=True)),
        ]
    }

    family_individual_aggs = {
        agg.pop('family_id'): agg for agg in Individual.objects.filter(family_id__in=families_by_id).values('family_id').annotate(
            **{k: v['agg'] for k, v in FAMILY_INDIVIDUAL_FIELDS.items()}
        )
    }
    for family_id, family in families_by_id.items():
        individual_agg = family_individual_aggs.get(family_id, {})
        id_guid_map = {i['id']: i['guid'] for i in individual_agg.get('parental_ids', [])}
        family.update({
            'individualGuids': sorted(id_guid_map.values()),
            **{config.get('response_key', key): _get_formatted_value(individual_agg.get(key), config, id_guid_map)
               for key, config in FAMILY_INDIVIDUAL_FIELDS.items()},
            **{key: family_id in data_families for key, data_families in has_data_families.items()},
        })

    response = families_discovery_tags(families, project=project)
    return create_json_response(response)


@login_and_policies_required
def project_overview(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    sample_load_counts, sample_models = _sample_load_counts(
        Sample, project, 'sample_type', 'dataset_type', loadedDate=TruncDate('loaded_date'),
    )
    rna_sample_load_counts, _ = _sample_load_counts(
        RnaSample, project, sample_type=Value('RNA'), dataset_type=F('data_type'), loadedDate=TruncDate('created_date'),
    )

    first_loaded_samples = sample_models.order_by('individual__family', 'loaded_date').distinct('individual__family').values_list('id', flat=True)
    samples = sample_models.filter(Q(is_active=True) | Q(id__in=first_loaded_samples))
    samples_by_guid = {s['sampleGuid']: s for s in get_json_for_samples(samples, project_guid=project_guid)}

    grouped_sample_counts = defaultdict(list)
    for s in sample_load_counts + rna_sample_load_counts:
        s['familyCounts'] = {f: s['familyCounts'].count(f) for f in s['familyCounts']}
        grouped_sample_counts[f'{s.pop("sample_type")}__{s.pop("dataset_type")}'].append(s)

    project_json = {'projectGuid': project_guid, 'sampleCounts': grouped_sample_counts}
    response = {
        'samplesByGuid': samples_by_guid,
    }

    add_project_tag_type_counts(project, response, project_json=project_json)

    project_mme_submissions = MatchmakerSubmission.objects.filter(individual__family__project=project)

    project_json = response['projectsByGuid'][project_guid]
    project_json.update({
        'mmeSubmissionCount': project_mme_submissions.filter(deleted_date__isnull=True).count(),
        'mmeDeletedSubmissionCount': project_mme_submissions.filter(deleted_date__isnull=False).count(),
    })

    return create_json_response(response)


def _sample_load_counts(sample_cls, project, *args, **kwargs):
    sample_models = sample_cls.objects.filter(individual__family__project=project)
    return list(sample_models.values(*args, **kwargs).order_by('loadedDate').annotate(
        familyCounts=ArrayAgg('individual__family__guid'))
    ), sample_models


@login_and_policies_required
def project_collaborators(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    return create_json_response({
        'projectsByGuid': {project_guid: {
            'collaborators': get_json_for_project_collaborator_list(request.user, project),
            'collaboratorGroups': get_json_for_project_collaborator_groups(project),
        }}
    })


@login_and_policies_required
def project_individuals(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    individuals = _get_json_for_individuals(
        Individual.objects.filter(family__project=project), user=request.user, project_guid=project_guid,
        add_hpo_details=True, has_case_review_perm=has_case_review_permissions(project, request.user))

    return create_json_response({
        'individualsByGuid': {i['individualGuid']: i for i in individuals},
    })


@login_and_policies_required
def project_samples(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    samples = Sample.objects.filter(individual__family__project=project)

    return create_json_response({
        'samplesByGuid': {s['sampleGuid']: s for s in get_json_for_samples(samples, project_guid=project_guid)},
    })


@login_and_policies_required
def project_analysis_groups(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    return create_json_response({
        'analysisGroupsByGuid': get_project_analysis_groups([project], project_guid)
    })


@login_and_policies_required
def project_locus_lists(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    locus_list_json, _ = get_project_locus_lists([project], request.user, include_metadata=True)

    return create_json_response({
        'projectsByGuid': {project_guid: {'locusListGuids': list(locus_list_json.keys())}},
        'locusListsByGuid': locus_list_json,
    })


@login_and_policies_required
def project_family_notes(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    family_notes = get_json_for_family_notes(FamilyNote.objects.filter(family__project=project), is_analyst=False)

    return create_json_response({
        'familyNotesByGuid': {n['noteGuid']: n for n in family_notes},
    })

@login_and_policies_required
def project_mme_submisssions(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    models = MatchmakerSubmission.objects.filter(
        individual__family__project=project).prefetch_related('matchmakersubmissiongenes_set')

    submissions_by_guid = {s['submissionGuid']: s for s in get_json_for_matchmaker_submissions(models)}

    for model in models:
        gene_ids = model.matchmakersubmissiongenes_set.values_list('gene_id', flat=True)
        submissions_by_guid[model.guid]['geneIds'] = list(gene_ids)

    family_notes = get_json_for_family_notes(FamilyNote.objects.filter(family__project=project))

    return create_json_response({
        'mmeSubmissionsByGuid': submissions_by_guid,
        'familyNotesByGuid': {n['noteGuid']: n for n in family_notes},
    })


@login_and_policies_required
def project_notifications(request, project_guid, read_status):
    project = get_project_and_check_permissions(project_guid, request.user)
    is_subscriber = project.subscribers.user_set.filter(id=request.user.id).exists()
    if not is_subscriber:
        max_loaded = _project_notifications(
            project, request.user.notifications).aggregate(max_loaded=Max('timestamp'))['max_loaded']
        to_create = _project_notifications(project, Notification.objects).distinct('verb', 'timestamp')
        if max_loaded:
            to_create = to_create.filter(timestamp__gt=max_loaded)
        for notification in to_create:
            notification.pk = None  # causes django to create a new model with otherwise identical fields
            notification.unread = True
            notification.recipient = request.user
            notification.save()

    response = {'isSubscriber': is_subscriber}
    notifications = _project_notifications(project, request.user.notifications)
    if read_status == 'unread':
        response['readCount'] = notifications.read().count()
        notifications = notifications.unread()
    else:
        notifications = notifications.read()
    return create_json_response({
        f'{read_status}Notifications': [
            {'timestamp': n.naturaltime(), **{k: getattr(n, k) for k in ['id', 'verb']}}
            for n in notifications],
        **response,
    })


def _project_notifications(project, notifications):
    return notifications.filter(actor_object_id=project.id)


@login_and_policies_required
def mark_read_project_notifications(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    _project_notifications(project, request.user.notifications).mark_all_as_read()
    return create_json_response({'readCount': request.user.notifications.read().count(), 'unreadNotifications': []})


@login_and_policies_required
def subscribe_project_notifications(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    request.user.groups.add(project.subscribers)
    return create_json_response({'isSubscriber': True})


def _delete_project(project_guid, user):
    """Delete project.

    Args:
        project_guid (string): GUID of the project to delete
        user (object): Django ORM model for the user
    """
    project = Project.objects.get(guid=project_guid)
    check_user_created_object_permissions(project, user)

    individual_guids_to_delete = Individual.objects.filter(
        family__project__guid=project_guid).values_list('guid', flat=True)
    delete_individuals(project, individual_guids_to_delete, user)

    Family.bulk_delete(user, project=project)

    project.delete_model(user, user_can_delete=True)

    if anvil_enabled() and not is_internal_anvil_project(project):
        AirtableSession(user, base=AirtableSession.ANVIL_BASE).safe_patch_records(
            ANVIL_REQUEST_TRACKING_TABLE,
            record_or_filters={'Status': ['Loading', 'Loading Requested', 'Loading request canceled', 'Available in Seqr']},
            record_and_filters={'AnVIL Project URL': f'{BASE_URL}project/{project_guid}/project_page'},
            update={'Status': 'Project Deleted'},
        )
