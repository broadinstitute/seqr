"""
APIs for updating project metadata, as well as creating or deleting projects
"""

import json
from django.db.models import Count
from django.utils import timezone

from matchmaker.models import MatchmakerSubmission
from seqr.models import Project, Family, Individual, Sample, IgvSample, VariantTag, VariantNote, SavedVariant, \
    ProjectCategory
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_project_from_json, create_model_from_json
from seqr.views.utils.orm_to_json_utils import _get_json_for_project, get_json_for_saved_variants, \
    get_json_for_project_collaborator_list, get_json_for_matchmaker_submissions
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions, \
    check_user_created_object_permissions, pm_required, user_is_analyst, login_and_policies_required
from seqr.views.utils.project_context_utils import get_projects_child_entities
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

    missing_fields = [field for field in ['name', 'genomeVersion'] if not request_json.get(field)]
    if missing_fields:
        error = 'Field(s) "{}" are required'.format(', '.join(missing_fields))
        return create_json_response({'error': error}, status=400, reason=error)

    project_args = {
        'name': request_json['name'],
        'genome_version': request_json['genomeVersion'],
        'description': request_json.get('description', ''),
    }

    project = create_model_from_json(Project, project_args, user=request.user)
    if ANALYST_PROJECT_CATEGORY:
        ProjectCategory.objects.get(name=ANALYST_PROJECT_CATEGORY).projects.add(project)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


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
    update_project_from_json(project, request_json, request.user, allow_unknown_keys=True)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


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
    """Returns a JSON object containing information used by the project page:
    ::

      json_response = {
         'project': {..},
         'familiesByGuid': {..},
         'individualsByGuid': {..},
         'samplesByGuid': {..},
       }

    Args:
        project_guid (string): GUID of the Project to retrieve data for.
    """
    project = get_project_and_check_permissions(project_guid, request.user)
    update_project_from_json(project, {'last_accessed_date': timezone.now()}, request.user)

    is_analyst = user_is_analyst(request.user)
    response = get_projects_child_entities([project], request.user, is_analyst=is_analyst)

    for i in response['individualsByGuid'].values():
        i['mmeSubmissionGuid'] = None
    response['mmeSubmissionsByGuid'] = _retrieve_mme_submissions(project, response['individualsByGuid'])

    project_json = response['projectsByGuid'][project_guid]
    project_json['collaborators'] = get_json_for_project_collaborator_list(request.user, project)
    project_json['detailsLoaded'] = True
    project_json['discoveryTags'] = _get_discovery_tags(project)

    _add_tag_type_counts(project, project_json['variantTagTypes'])
    project_json['variantTagTypes'] = sorted(project_json['variantTagTypes'], key=lambda variant_tag_type: variant_tag_type['order'] or 0)

    gene_ids = set()
    for tag in project_json['discoveryTags']:
        gene_ids.update(list(tag.get('transcripts', {}).keys()))
    for submission in response['mmeSubmissionsByGuid'].values():
        gene_ids.update(submission['geneIds'])

    response.update({
        'genesById': get_genes(gene_ids),
    })

    return create_json_response(response)


def _retrieve_mme_submissions(project, individuals_by_guid):
    models = MatchmakerSubmission.objects.filter(individual__family__project=project)

    submissions = get_json_for_matchmaker_submissions(models, additional_model_fields=['genomic_features'])

    submissions_by_guid = {}
    for s in submissions:
        genomic_features = s.pop('genomicFeatures') or []
        s['geneIds'] = [feature['gene']['id'] for feature in genomic_features if feature.get('gene', {}).get('id')]
        guid = s['submissionGuid']
        submissions_by_guid[guid] = s

        individual_guid = s['individualGuid']
        individuals_by_guid[individual_guid]['mmeSubmissionGuid'] = guid

    return submissions_by_guid


def _add_tag_type_counts(project, project_variant_tags):
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
        'numTagsPerFamily': {count['saved_variants__family__guid']: count['count'] for count in note_counts_by_family},
    }

    tag_counts_by_type_and_family = VariantTag.objects.filter(saved_variants__family__project=project)\
        .values('saved_variants__family__guid', 'variant_tag_type__name').annotate(count=Count('*'))
    for tag_type in project_variant_tags:
        current_tag_type_counts = [counts for counts in tag_counts_by_type_and_family if
                                   counts['variant_tag_type__name'] == tag_type['name']]
        num_tags = sum(count['count'] for count in current_tag_type_counts)
        tag_type.update({
            'numTags': num_tags,
            'numTagsPerFamily': {count['saved_variants__family__guid']: count['count'] for count in
                                 current_tag_type_counts},
        })

    project_variant_tags.append(note_tag_type)


def _get_discovery_tags(project):
    discovery_tags = get_json_for_saved_variants(SavedVariant.objects.filter(
        family__project=project, varianttag__variant_tag_type__category='CMG Discovery Tags',
    ), add_details=True)

    return discovery_tags


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
