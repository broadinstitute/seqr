"""
APIs for updating project metadata, as well as creating or deleting projects
"""

import json
import logging
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone

from matchmaker.models import MatchmakerSubmission
from seqr.models import Project, Family, Individual, Sample, IgvSample, VariantTag, VariantFunctionalData, \
    VariantNote, VariantTagType, SavedVariant, AnalysisGroup, LocusList
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_project_from_json, get_or_create_model_from_json
from seqr.views.utils.orm_to_json_utils import _get_json_for_project, get_json_for_samples, _get_json_for_families, \
    _get_json_for_individuals, get_json_for_saved_variants, get_json_for_analysis_groups, \
    get_json_for_variant_functional_data_tag_types, get_json_for_locus_lists, \
    get_json_for_project_collaborator_list, _get_json_for_models, get_json_for_matchmaker_submissions
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_project_permissions
from settings import API_LOGIN_REQUIRED_URL


logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
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

    name = request_json.get('name')
    if not name:
        return create_json_response({}, status=400, reason="'Name' cannot be blank")

    description = request_json.get('description', '')
    genome_version = request_json.get('genomeVersion')

    project = _create_project(name, request.user, description=description, genome_version=genome_version)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
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


@login_required(login_url=API_LOGIN_REQUIRED_URL)
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


@login_required(login_url=API_LOGIN_REQUIRED_URL)
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

    response = _get_project_child_entities(project, request.user)

    project_json = _get_json_for_project(project, request.user)
    project_json['collaborators'] = get_json_for_project_collaborator_list(project)
    project_json['locusListGuids'] = list(response['locusListsByGuid'].keys())
    project_json['detailsLoaded'] = True
    project_json.update(_get_json_for_variant_tag_types(project))

    gene_ids = set()
    for tag in project_json['discoveryTags']:
        gene_ids.update(list(tag.get('transcripts', {}).keys()))
    for submission in response['mmeSubmissionsByGuid'].values():
        gene_ids.update(submission['geneIds'])

    response.update({
        'projectsByGuid': {project_guid: project_json},
        'genesById': get_genes(gene_ids),
    })
    return create_json_response(response)


def _get_project_child_entities(project, user):
    families_by_guid = _retrieve_families(project.guid, user)
    individuals_by_guid, individual_models = _retrieve_individuals(project.guid, user)
    for individual_guid, individual in individuals_by_guid.items():
        families_by_guid[individual['familyGuid']]['individualGuids'].add(individual_guid)
    samples_by_guid = _retrieve_samples(
        project.guid, individuals_by_guid, Sample.objects.filter(individual__in=individual_models))
    igv_samples_by_guid = _retrieve_samples(
        project.guid, individuals_by_guid, IgvSample.objects.filter(individual__in=individual_models),
        sample_guid_key='igvSampleGuids')
    mme_submissions_by_guid = _retrieve_mme_submissions(individuals_by_guid, individual_models)
    analysis_groups_by_guid = _retrieve_analysis_groups(project)
    locus_lists = get_json_for_locus_lists(LocusList.objects.filter(projects__id=project.id), user)
    locus_lists_by_guid = {locus_list['locusListGuid']: locus_list for locus_list in locus_lists}
    return {
        'familiesByGuid': families_by_guid,
        'individualsByGuid': individuals_by_guid,
        'samplesByGuid': samples_by_guid,
        'igvSamplesByGuid': igv_samples_by_guid,
        'locusListsByGuid': locus_lists_by_guid,
        'analysisGroupsByGuid': analysis_groups_by_guid,
        'mmeSubmissionsByGuid': mme_submissions_by_guid,
    }


def _retrieve_families(project_guid, user):
    """Retrieves family-level metadata for the given project.

    Args:
        project_guid (string): project_guid
        user (Model): for checking permissions to view certain fields
    Returns:
        dictionary: families_by_guid
    """
    fields = Family._meta.json_fields + Family._meta.internal_json_fields
    family_models = Family.objects.filter(project__guid=project_guid).only(*fields)

    families = _get_json_for_families(family_models, user, project_guid=project_guid)

    families_by_guid = {}
    for family in families:
        family_guid = family['familyGuid']
        family['individualGuids'] = set()
        families_by_guid[family_guid] = family

    return families_by_guid


def _retrieve_individuals(project_guid, user):
    """Retrieves individual-level metadata for the given project.

    Args:
        project_guid (string): project_guid
    Returns:
        dictionary: individuals_by_guid
    """

    individual_models = Individual.objects.filter(family__project__guid=project_guid)

    individuals = _get_json_for_individuals(
        individual_models, user=user, project_guid=project_guid, add_hpo_details=True)

    individuals_by_guid = {}
    for i in individuals:
        i['sampleGuids'] = set()
        i['igvSampleGuids'] = set()
        i['mmeSubmissionGuid'] = None
        individual_guid = i['individualGuid']
        individuals_by_guid[individual_guid] = i

    return individuals_by_guid, individual_models


def _retrieve_samples(project_guid, individuals_by_guid, sample_models, sample_guid_key='sampleGuids'):
    """Retrieves sample metadata for the given project.

        Args:
            project_guid (string): project_guid
            individuals_by_guid (dict): maps each individual_guid to a dictionary with individual info.
                This method adds a "sampleGuids" list to each of these dictionaries.
        Returns:
            2-tuple with dictionaries: (samples_by_guid, sample_batches_by_guid)
        """
    samples = get_json_for_samples(sample_models, project_guid=project_guid)

    samples_by_guid = {}
    for s in samples:
        sample_guid = s['sampleGuid']
        samples_by_guid[sample_guid] = s

        individual_guid = s['individualGuid']
        individuals_by_guid[individual_guid][sample_guid_key].add(sample_guid)

    return samples_by_guid


def _retrieve_mme_submissions(individuals_by_guid, individual_models):
    models = MatchmakerSubmission.objects.filter(individual__in=individual_models)

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


def _retrieve_analysis_groups(project):
    group_models = AnalysisGroup.objects.filter(project=project)
    groups = get_json_for_analysis_groups(group_models, project_guid=project.guid)
    return {group['analysisGroupGuid']: group for group in groups}


def _get_json_for_variant_tag_types(project):
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
    project_variant_tags = _get_json_for_models(VariantTagType.objects.filter(Q(project=project) | Q(project__isnull=True)))
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
    project_variant_tags = sorted(project_variant_tags, key=lambda variant_tag_type: variant_tag_type['order'] or 0)

    discovery_tag_type_guids = [tag_type['variantTagTypeGuid'] for tag_type in project_variant_tags
                                if tag_type['category'] == 'CMG Discovery Tags' and tag_type['numTags'] > 0]
    discovery_tags = get_json_for_saved_variants(SavedVariant.objects.filter(
        family__project=project, varianttag__variant_tag_type__guid__in=discovery_tag_type_guids,
    ), add_details=True)

    project_functional_tags = []
    for category, tags in VariantFunctionalData.FUNCTIONAL_DATA_CHOICES:
        project_functional_tags += [{
            'category': category,
            'name': name,
            'metadataTitle': json.loads(tag_json).get('metadata_title'),
            'color': json.loads(tag_json)['color'],
            'description': json.loads(tag_json).get('description'),
        } for name, tag_json in tags]

    return {
        'variantTagTypes': sorted(project_variant_tags, key=lambda variant_tag_type: variant_tag_type['order'] or 0),
        'variantFunctionalTagTypes': get_json_for_variant_functional_data_tag_types(),
        'discoveryTags': discovery_tags,
    }


def _create_project(name, user, description=None, genome_version=None):
    """Creates a new project.

    Args:
        name (string): Project name
        description (string): optional description
        user (object): Django user that is creating this project
    """
    project_args = {
        'name': name,
        'description': description,
        'created_by': user,
    }
    if genome_version:
        project_args['genome_version'] = genome_version

    project, _ = get_or_create_model_from_json(Project, project_args, update_json=None, user=user)

    return project


def _delete_project(project_guid, user):
    """Delete project.

    Args:
        project_guid (string): GUID of the project to delete
        user (object): Django ORM model for the user
    """
    project = get_project_and_check_permissions(project_guid, user, is_owner=True)

    IgvSample.bulk_delete(user, individual__family__project=project)
    Sample.bulk_delete(user, individual__family__project=project)

    Individual.bulk_delete(user, family__project=project)

    Family.bulk_delete(user, project=project)

    project.delete_model(user, user_can_delete=True)
