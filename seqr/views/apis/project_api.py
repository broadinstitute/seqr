"""
APIs for updating project metadata, as well as creating or deleting projects
"""

import json
import logging
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Project, Family, Individual, Sample, VariantTag, VariantFunctionalData, \
    VariantNote, VariantTagType, AnalysisGroup, _slugify, CAN_EDIT, IS_OWNER
from seqr.utils.gene_utils import get_genes
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.json_to_orm_utils import update_project_from_json
from seqr.views.utils.orm_to_json_utils import _get_json_for_project, get_json_for_samples, _get_json_for_families, \
    _get_json_for_individuals, get_json_for_saved_variants, get_json_for_analysis_groups, \
    get_json_for_variant_functional_data_tag_types, get_sorted_project_locus_lists, \
    get_json_for_project_collaborator_list, _get_json_for_models
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_permissions
from seqr.views.utils.phenotips_utils import create_phenotips_user, get_phenotips_uname_and_pwd_for_project, \
    delete_phenotips_patient
from seqr.views.utils.individual_utils import export_individuals
from settings import PHENOTIPS_SERVER, API_LOGIN_REQUIRED_URL


logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
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

    #if not created:
    #    return create_json_response({}, status=400, reason="A project named '%(name)s' already exists" % locals())

    project = _create_project(name, description=description, genome_version=genome_version, user=request.user)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
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

    check_permissions(project, request.user, CAN_EDIT)

    request_json = json.loads(request.body)
    update_project_from_json(project, request_json, allow_unknown_keys=True)

    return create_json_response({
        'projectsByGuid': {
            project.guid: _get_json_for_project(project, request.user)
        },
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_project_handler(request, project_guid):
    """Delete project - request handler.

    Args:
        project_guid (string): GUID of the project to delete
    """

    project = get_project_and_check_permissions(project_guid, request.user, permission_level=IS_OWNER)

    _delete_project(project)

    return create_json_response({
        'projectsByGuid': {
            project.guid: None
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
    update_project_from_json(project, {'last_accessed_date': timezone.now()})

    families_by_guid, individuals_by_guid, samples_by_guid, analysis_groups_by_guid, locus_lists_by_guid = _get_project_child_entities(project, request.user)

    project_json = _get_json_for_project(project, request.user)
    project_json['collaborators'] = get_json_for_project_collaborator_list(project)
    project_json['locusListGuids'] = locus_lists_by_guid.keys()
    project_json['detailsLoaded'] = True
    project_json.update(_get_json_for_variant_tag_types(project))

    gene_ids = set()
    for tag in project_json['discoveryTags']:
        gene_ids.update(tag['transcripts'].keys())

    return create_json_response({
        'projectsByGuid': {project_guid: project_json},
        'familiesByGuid': families_by_guid,
        'individualsByGuid': individuals_by_guid,
        'samplesByGuid': samples_by_guid,
        'locusListsByGuid': locus_lists_by_guid,
        'analysisGroupsByGuid': analysis_groups_by_guid,
        'genesById': get_genes(gene_ids),
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def export_project_individuals_handler(request, project_guid):
    """Export project Individuals table.

    Args:
        project_guid (string): GUID of the project for which to export individual data
    """

    file_format = request.GET.get('file_format', 'tsv')
    include_phenotypes = bool(request.GET.get('include_phenotypes'))

    project = get_project_and_check_permissions(project_guid, request.user)

    # get all individuals in this project
    individuals = Individual.objects.filter(family__project=project).order_by('family__family_id', 'affected')

    filename_prefix = "%s_individuals" % _slugify(project.name)

    return export_individuals(
        filename_prefix,
        individuals,
        file_format,
        include_hpo_terms_present=include_phenotypes,
        include_hpo_terms_absent=include_phenotypes,
    )


def _get_project_child_entities(project, user):
    families_by_guid = _retrieve_families(project.guid, user)
    individuals_by_guid = _retrieve_individuals(project.guid, user)
    for individual_guid, individual in individuals_by_guid.items():
        families_by_guid[individual['familyGuid']]['individualGuids'].add(individual_guid)
    samples_by_guid = _retrieve_samples(project.guid, individuals_by_guid)
    analysis_groups_by_guid = _retrieve_analysis_groups(project)
    locus_lists = get_sorted_project_locus_lists(project, user)
    locus_lists_by_guid = {locus_list['locusListGuid']: locus_list for locus_list in locus_lists}
    return families_by_guid, individuals_by_guid, samples_by_guid, analysis_groups_by_guid, locus_lists_by_guid


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

    individuals = _get_json_for_individuals(individual_models, user=user, project_guid=project_guid)

    individuals_by_guid = {}
    for i in individuals:
        i['sampleGuids'] = set()
        individual_guid = i['individualGuid']
        individuals_by_guid[individual_guid] = i

    return individuals_by_guid


def _retrieve_samples(project_guid, individuals_by_guid):
    """Retrieves sample metadata for the given project.

        Args:
            project_guid (string): project_guid
            individuals_by_guid (dict): maps each individual_guid to a dictionary with individual info.
                This method adds a "sampleGuids" list to each of these dictionaries.
        Returns:
            2-tuple with dictionaries: (samples_by_guid, sample_batches_by_guid)
        """
    sample_models = Sample.objects.filter(individual__family__project__guid=project_guid)

    samples = get_json_for_samples(sample_models, project_guid=project_guid)

    samples_by_guid = {}
    for s in samples:
        sample_guid = s['sampleGuid']
        samples_by_guid[sample_guid] = s

        individual_guid = s['individualGuid']
        individuals_by_guid[individual_guid]['sampleGuids'].add(sample_guid)

    return samples_by_guid


def _retrieve_analysis_groups(project):
    group_models = AnalysisGroup.objects.filter(project=project)
    groups = get_json_for_analysis_groups(group_models, project_guid=project.guid)
    return {group['analysisGroupGuid']: group for group in groups}


def _get_json_for_variant_tag_types(project):
    note_counts_by_family = VariantNote.objects.filter(saved_variant__family__project=project).values('saved_variant__family__guid').annotate(count=Count('*'))
    num_tags = sum(count['count'] for count in note_counts_by_family)
    note_tag_type = {
        'variantTagTypeGuid': 'notes',
        'name': 'Has Notes',
        'category': 'Notes',
        'description': '',
        'color': 'grey',
        'order': 100,
        'is_built_in': True,
        'numTags': num_tags,
        'numTagsPerFamily': {count['saved_variant__family__guid']: count['count'] for count in note_counts_by_family},
    }

    tag_counts_by_type_and_family = VariantTag.objects.filter(saved_variant__family__project=project).values('saved_variant__family__guid', 'variant_tag_type__name').annotate(count=Count('*'))
    project_variant_tags = _get_json_for_models(VariantTagType.objects.filter(Q(project=project) | Q(project__isnull=True)))
    for tag_type in project_variant_tags:
        current_tag_type_counts = [counts for counts in tag_counts_by_type_and_family if
                                   counts['variant_tag_type__name'] == tag_type['name']]
        num_tags = sum(count['count'] for count in current_tag_type_counts)
        tag_type.update({
            'numTags': num_tags,
            'numTagsPerFamily': {count['saved_variant__family__guid']: count['count'] for count in
                                 current_tag_type_counts},
        })

    project_variant_tags.append(note_tag_type)
    project_variant_tags = sorted(project_variant_tags, key=lambda variant_tag_type: variant_tag_type['order'])

    discovery_tags = []
    for tag_type in project_variant_tags:
        if tag_type['category'] == 'CMG Discovery Tags' and tag_type['numTags'] > 0:
            tags = VariantTag.objects.filter(saved_variant__family__project=project, variant_tag_type__guid=tag_type['variantTagTypeGuid']).select_related('saved_variant')
            saved_variants = [tag.saved_variant for tag in tags]
            discovery_tags += get_json_for_saved_variants(saved_variants, add_tags=True, add_details=True)

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
        'variantTagTypes': sorted(project_variant_tags, key=lambda variant_tag_type: variant_tag_type['order']),
        'variantFunctionalTagTypes': get_json_for_variant_functional_data_tag_types(),
        'discoveryTags': discovery_tags,
    }


def _create_project(name, description=None, genome_version=None, user=None):
    """Creates a new project.

    Args:
        name (string): Project name
        description (string): optional description
        user (object): Django user that is creating this project
    """
    if not name:
        raise ValueError("Name not specified: %s" % (name,))

    project_args = {
        'name': name,
        'description': description,
        'created_by': user,
        'deprecated_project_id': _slugify(name),
    }
    if genome_version:
        project_args['genome_version'] = genome_version

    project, _ = Project.objects.get_or_create(**project_args)

    if PHENOTIPS_SERVER:
        try:
            _enable_phenotips_for_project(project)
        except Exception as e:
            logger.error("Unable to create patient in PhenoTips. Make sure PhenoTips is running: %s", e)
            raise

    return project


def _delete_project(project):
    """Delete project.

    Args:
        project (object): Django ORM model for the project to delete
    """

    Sample.objects.filter(individual__family__project=project).delete()

    individuals = Individual.objects.filter(family__project=project)
    for individual in individuals:
        delete_phenotips_patient(project, individual)
    individuals.delete()

    Family.objects.filter(project=project).delete()

    project.delete()


def _enable_phenotips_for_project(project):
    """Creates 2 users in PhenoTips for this project (one that will be view-only and one that'll
    have edit permissions for patients in the project).
    """
    project.is_phenotips_enabled = True
    project.phenotips_user_id = _slugify(project.name)

    # view-only user
    username, password = get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=True)
    create_phenotips_user(username, password)

    # user with edit permissions
    username, password = get_phenotips_uname_and_pwd_for_project(project.phenotips_user_id, read_only=False)
    create_phenotips_user(username, password)
    project.save()
