"""
APIs for updating project metadata, as well as creating or deleting projects
"""

import json
from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max
from django.utils import timezone

from matchmaker.models import MatchmakerSubmission
from seqr.models import Project, Family, Individual, Sample, IgvSample, VariantTag, VariantNote, \
    ProjectCategory, FamilyNote, CAN_EDIT
from seqr.views.utils.json_utils import create_json_response, _to_snake_case
from seqr.views.utils.json_to_orm_utils import update_project_from_json, create_model_from_json, update_model_from_json
from seqr.views.utils.orm_to_json_utils import _get_json_for_project, \
    get_json_for_project_collaborator_list, get_json_for_matchmaker_submissions, _get_json_for_families, \
    get_json_for_family_notes, _get_json_for_individuals
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions, \
    check_user_created_object_permissions, pm_required, user_is_pm, user_is_analyst, login_and_policies_required, \
    has_workspace_perm
from seqr.views.utils.project_context_utils import get_projects_child_entities, families_discovery_tags, \
    add_project_tag_types, get_project_analysis_groups
from seqr.views.utils.terra_api_utils import is_anvil_authenticated
from settings import ANALYST_PROJECT_CATEGORY


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
    if ANALYST_PROJECT_CATEGORY:
        ProjectCategory.objects.get(name=ANALYST_PROJECT_CATEGORY).projects.add(project)

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


@login_and_policies_required
def project_families(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    family_models = Family.objects.filter(project=project)
    families = _get_json_for_families(
        family_models, request.user, project_guid=project_guid, add_individual_guids_field=True
    )
    response = families_discovery_tags(families)
    has_features_families = set(family_models.filter(individual__features__isnull=False).values_list('guid', flat=True))
    annotated_models = family_models.annotate(
        case_review_statuses=ArrayAgg('individual__case_review_status', distinct=True),
        case_review_status_last_modified=Max('individual__case_review_status_last_modified_date')
    )
    for family in annotated_models:
        response['familiesByGuid'][family.guid].update({
            'caseReviewStatuses': family.case_review_statuses,
            'caseReviewStatusLastModified': family.case_review_status_last_modified,
            'hasFeatures': family.guid in has_features_families,
        })
    response['projectsByGuid'] = {project_guid: {'familiesLoaded': True}}
    return create_json_response(response)


@login_and_policies_required
def project_overview(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    is_analyst = user_is_analyst(request.user)
    response = get_projects_child_entities([project], project.guid, request.user, is_analyst=is_analyst)
    add_project_tag_types(response['projectsByGuid'])

    project_mme_submissions = MatchmakerSubmission.objects.filter(individual__family__project=project)

    project_json = response['projectsByGuid'][project_guid]
    project_json.update({
        'detailsLoaded': True,
        'collaborators': get_json_for_project_collaborator_list(request.user, project),
        'mmeSubmissionCount': project_mme_submissions.filter(deleted_date__isnull=True).count(),
        'mmeDeletedSubmissionCount': project_mme_submissions.filter(deleted_date__isnull=False).count(),
    })

    response['familyTagTypeCounts'] = _add_tag_type_counts(project, project_json['variantTagTypes'])

    return create_json_response(response)

@login_and_policies_required
def project_individuals(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    individuals = _get_json_for_individuals(
        Individual.objects.filter(family__project=project), user=request.user, project_guid=project_guid, add_hpo_details=True)

    return create_json_response({
        'projectsByGuid': {project_guid: {'individualsLoaded': True}},
        'individualsByGuid': {i['individualGuid']: i for i in individuals},
    })

@login_and_policies_required
def project_analysis_groups(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    return create_json_response({
        'projectsByGuid': {project_guid: {'analysisGroupsLoaded': True}},
        'analysisGroupsByGuid': get_project_analysis_groups([project], project_guid)
    })

@login_and_policies_required
def project_family_notes(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    family_notes = get_json_for_family_notes(FamilyNote.objects.filter(family__project=project), is_analyst=False)

    return create_json_response({
        'projectsByGuid': {project_guid: {'familyNotesLoaded': True}},
        'familyNotesByGuid': {n['noteGuid']: n for n in family_notes},
    })

@login_and_policies_required
def project_mme_submisssions(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    models = MatchmakerSubmission.objects.filter(individual__family__project=project)

    submissions = get_json_for_matchmaker_submissions(models, additional_model_fields=['genomic_features'])

    submissions_by_guid = {}
    for s in submissions:
        genomic_features = s.pop('genomicFeatures') or []
        s['geneIds'] = [feature['gene']['id'] for feature in genomic_features if feature.get('gene', {}).get('id')]
        guid = s['submissionGuid']
        submissions_by_guid[guid] = s

    family_notes = get_json_for_family_notes(FamilyNote.objects.filter(family__project=project))

    return create_json_response({
        'projectsByGuid': {project_guid: {'mmeSubmissionsLoaded': True}},
        'mmeSubmissionsByGuid': submissions_by_guid,
        'familyNotesByGuid': {n['noteGuid']: n for n in family_notes},
    })


def _add_tag_type_counts(project, project_variant_tags):
    family_tag_type_counts = defaultdict(dict)
    note_counts_by_family = VariantNote.objects.filter(saved_variants__family__project=project)\
        .values('saved_variants__family__guid').annotate(count=Count('*'))
    num_tags = sum(count['count'] for count in note_counts_by_family)
    note_tag_type = {
        'variantTagTypeGuid': 'notes',
        'name': 'Has Notes',
        'category': 'Notes',
        'description': '',
        'color': 'grey',
        'order': 100,
        'numTags': num_tags,
    }

    tag_counts_by_type_and_family = VariantTag.objects.filter(saved_variants__family__project=project)\
        .values('saved_variants__family__guid', 'variant_tag_type__name').annotate(count=Count('guid', distinct=True))
    for tag_type in project_variant_tags:
        current_tag_type_counts = [counts for counts in tag_counts_by_type_and_family if
                                   counts['variant_tag_type__name'] == tag_type['name']]
        num_tags = sum(count['count'] for count in current_tag_type_counts)
        tag_type.update({
            'numTags': num_tags,
        })
        for count in current_tag_type_counts:
            family_tag_type_counts[count['saved_variants__family__guid']].update({tag_type['name']: count['count']})

    project_variant_tags.append(note_tag_type)
    return family_tag_type_counts


def _delete_project(project_guid, user):
    """Delete project.

    Args:
        project_guid (string): GUID of the project to delete
        user (object): Django ORM model for the user
    """
    project = Project.objects.get(guid=project_guid)
    check_user_created_object_permissions(project, user)

    IgvSample.bulk_delete(user, individual__family__project=project)
    Sample.bulk_delete(user, individual__family__project=project)

    Individual.bulk_delete(user, family__project=project)

    Family.bulk_delete(user, project=project)

    project.delete_model(user, user_can_delete=True)
