"""
APIs used by the project page
"""

import itertools
import logging
import json

from guardian.shortcuts import get_objects_for_group
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Q, Count

from seqr.models import Family, Individual, _slugify, CAN_VIEW, LocusList, \
    LocusListGene, LocusListInterval, VariantTagType, VariantTag, VariantFunctionalData
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.family_api import export_families
from seqr.views.apis.individual_api import export_individuals
from seqr.views.utils.family_info_utils import retrieve_multi_family_analysed_by
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_project, _get_json_for_sample, _get_json_for_families, _get_json_for_individuals


from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from xbrowse_server.mall import get_project_datastore
from xbrowse_server.base.models import Project as BaseProject

logger = logging.getLogger(__name__)


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

    cursor = connection.cursor()

    families_by_guid = _retrieve_families(cursor, project.guid, request.user)
    individuals_by_guid = _retrieve_individuals(project.guid, request.user)
    for individual_guid, individual in individuals_by_guid.items():
        families_by_guid[individual['familyGuid']]['individualGuids'].add(individual_guid)
    samples_by_guid = _retrieve_samples(cursor, project.guid, individuals_by_guid)

    cursor.close()

    project_json = _get_json_for_project(project, request.user)
    project_json['collaborators'] = _get_json_for_collaborator_list(project)
    project_json['locusLists'] = _get_json_for_locus_lists(project)
    project_json.update(_get_json_for_variant_tag_types(project))
    #project_json['referencePopulations'] = _get_json_for_reference_populations(project)

    # gene search will be deprecated once the new database is online.
    project_json['hasGeneSearch'] = _has_gene_search(project)
    project_json['detailsLoaded'] = True

    json_response = {
        'project': project_json,
        'familiesByGuid': families_by_guid,
        'individualsByGuid': individuals_by_guid,
        'samplesByGuid': samples_by_guid,
    }

    return create_json_response(json_response)


def _retrieve_families(cursor, project_guid, user):
    """Retrieves family-level metadata for the given project.

    Args:
        cursor: connected database cursor that can be used to execute SQL queries.
        project_guid (string): project_guid
        user (Model): for checking permissions to view certain fields
    Returns:
        dictionary: families_by_guid
    """

    families_query = """
        SELECT DISTINCT
          p.guid AS project_guid,
          f.id AS family_id,
          f.guid AS family_guid,
          f.family_id AS family_family_id,
          f.display_name AS family_display_name,
          f.description AS family_description,
          f.analysis_notes AS family_analysis_notes,
          f.analysis_summary AS family_analysis_summary,
          f.pedigree_image AS family_pedigree_image,
          f.analysis_status AS family_analysis_status,
          f.causal_inheritance_mode AS family_causal_inheritance_mode,
          f.internal_analysis_status AS family_internal_analysis_status,
          f.internal_case_review_notes AS family_internal_case_review_notes,
          f.internal_case_review_summary AS family_internal_case_review_summary
        FROM seqr_project AS p
          JOIN seqr_family AS f ON f.project_id=p.id
        WHERE p.guid=%s
    """.strip()

    cursor.execute(families_query, [project_guid])

    columns = [col[0] for col in cursor.description]
    family_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    families = _get_json_for_families(family_rows, user, add_analysed_by_field=False)

    analysed_by = retrieve_multi_family_analysed_by(families)
    families_by_guid = {}
    for family in families:
        family_guid = family['familyGuid']
        family['individualGuids'] = set()
        family['analysedBy'] = analysed_by[family_guid]
        families_by_guid[family_guid] = family

    return families_by_guid


def _retrieve_individuals(project_guid, user):
    """Retrieves individual-level metadata for the given project.

    Args:
        project_guid (string): project_guid
    Returns:
        dictionary: individuals_by_guid
    """

    fields = Individual._meta.json_fields + Individual._meta.internal_json_fields + \
             ['family__guid', 'case_review_status_last_modified_by__email']
    individual_models = Individual.objects.filter(family__project__guid=project_guid)\
        .select_related('family', 'case_review_status_last_modified_by').only(*fields)

    individuals = _get_json_for_individuals(individual_models, user=user, project_guid=project_guid)

    individuals_by_guid = {}
    for i in individuals:
        i['sampleGuids'] = set()
        individual_guid = i['individualGuid']
        individuals_by_guid[individual_guid] = i

    return individuals_by_guid


def _retrieve_samples(cursor, project_guid, individuals_by_guid):
    """Retrieves sample metadata for the given project.

        Args:
            cursor: connected database cursor that can be used to execute SQL queries.
            project_guid (string): project_guid
            individuals_by_guid (dict): maps each individual_guid to a dictionary with individual info.
                This method adds a "sampleGuids" list to each of these dictionaries.
        Returns:
            2-tuple with dictionaries: (samples_by_guid, sample_batches_by_guid)
        """

    # use raw SQL since the Django ORM doesn't have a good way to express these types of queries.
    sample_query = """
        SELECT
          p.guid AS project_guid,
          i.guid AS individual_guid,
          s.guid AS sample_guid,
          s.created_date AS sample_created_date,
          s.sample_type AS sample_sample_type,
          s.dataset_type AS sample_dataset_type,
          s.sample_id AS sample_sample_id,
          s.elasticsearch_index AS sample_elasticsearch_index,
          s.dataset_file_path AS sample_dataset_file_path,
          s.sample_status AS sample_sample_status,
          s.loaded_date AS sample_loaded_date
        FROM seqr_sample AS s
          JOIN seqr_individual AS i ON s.individual_id=i.id
          JOIN seqr_family AS f ON i.family_id=f.id
          JOIN seqr_project AS p ON f.project_id=p.id
        WHERE p.guid=%s
    """.strip()

    cursor.execute(sample_query, [project_guid])

    columns = [col[0] for col in cursor.description]

    samples_by_guid = {}
    for row in cursor.fetchall():
        record = dict(zip(columns, row))

        sample_guid = record['sample_guid']
        if sample_guid not in samples_by_guid:
            samples_by_guid[sample_guid] = _get_json_for_sample(record)

        individual_guid = record['individual_guid']
        individuals_by_guid[individual_guid]['sampleGuids'].add(sample_guid)

        samples_by_guid[sample_guid]['individualGuid'] = individual_guid

    return samples_by_guid


def _get_json_for_collaborator_list(project):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborator_list = []

    def _compute_json(collaborator, can_view, can_edit):
        return {
            'displayName': collaborator.profile.display_name,
            'username': collaborator.username,
            'email': collaborator.email,
            'firstName': collaborator.first_name,
            'lastName': collaborator.last_name,
            'hasViewPermissions': can_view,
            'hasEditPermissions': can_edit,
        }

    previously_added_ids = set()
    for collaborator in itertools.chain(project.owners_group.user_set.all(), project.can_edit_group.user_set.all()):
        if collaborator.id in previously_added_ids:
            continue
        previously_added_ids.add(collaborator.id)
        collaborator_list.append(
            _compute_json(collaborator, can_edit=True, can_view=True)
        )
    for collaborator in project.can_view_group.user_set.all():
        if collaborator.id in previously_added_ids:
            continue
        previously_added_ids.add(collaborator.id)
        collaborator_list.append(
            _compute_json(collaborator, can_edit=False, can_view=True)
        )

    return sorted(collaborator_list, key=lambda collaborator: (collaborator['lastName'], collaborator['displayName']))


def _get_json_for_locus_lists(project):
    result = []

    for locus_list in get_objects_for_group(project.can_view_group, CAN_VIEW, LocusList):
        result.append({
            'locusListGuid': locus_list.guid,
            'createdDate': locus_list.created_date,
            'name': locus_list.name,
            'deprecatedGeneListId': _slugify(locus_list.name),
            'description': locus_list.description,
            'numEntries': LocusListGene.objects.filter(locus_list=locus_list).count() + LocusListInterval.objects.filter(locus_list=locus_list).count(),
        })

    return sorted(result, key=lambda locus_list: locus_list['createdDate'])


def _get_json_for_variant_tag_types(project):
    project_variant_tags = []
    tag_counts_by_type_and_family = VariantTag.objects.filter(saved_variant__project=project).values('saved_variant__family__guid', 'variant_tag_type__name').annotate(count=Count('*'))
    for variant_tag_type in VariantTagType.objects.filter(Q(project=project) | Q(project__isnull=True)):
        current_tag_type_counts = [counts for counts in tag_counts_by_type_and_family if counts['variant_tag_type__name'] == variant_tag_type.name]
        project_variant_tags.append({
            'variantTagTypeGuid': variant_tag_type.guid,
            'name': variant_tag_type.name,
            'category': variant_tag_type.category,
            'description': variant_tag_type.description,
            'color': variant_tag_type.color,
            'order': variant_tag_type.order,
            'is_built_in': variant_tag_type.is_built_in,
            'numTags': sum(count['count'] for count in current_tag_type_counts),
            'numTagsPerFamily': {count['saved_variant__family__guid']: count['count'] for count in current_tag_type_counts},
        })

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
        'variantFunctionalTagTypes': project_functional_tags,
    }


"""
def _get_json_for_reference_populations(project):
    result = []

    for reference_populations in project.custom_reference_populations.all():
        result.append({
            'id': reference_populations.slug,
            'name': reference_populations.name,
        })

    return result
"""


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def export_project_families_handler(request, project_guid):
    """Export project Families table.

    Args:
        project_guid (string): GUID of the project for which to export family data
    """
    format = request.GET.get('file_format', 'tsv')

    project = get_project_and_check_permissions(project_guid, request.user)

    # get all families in this project
    families = Family.objects.filter(project=project).order_by('family_id')

    filename_prefix = "%s_families" % _slugify(project.name)

    return export_families(filename_prefix, families, format, include_internal_case_review_summary=False, include_internal_case_review_notes=False)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def export_project_individuals_handler(request, project_guid):
    """Export project Individuals table.

    Args:
        project_guid (string): GUID of the project for which to export individual data
    """

    format = request.GET.get('file_format', 'tsv')
    include_phenotypes = bool(request.GET.get('include_phenotypes'))

    project = get_project_and_check_permissions(project_guid, request.user)

    # get all individuals in this project
    individuals = Individual.objects.filter(family__project=project).order_by('family__family_id', 'affected')

    filename_prefix = "%s_individuals" % _slugify(project.name)

    return export_individuals(
        filename_prefix,
        individuals,
        format,
        include_hpo_terms_present=include_phenotypes,
        include_hpo_terms_absent=include_phenotypes,
    )


def _has_gene_search(project):
    """
    Returns True if this project has Gene Search enabled.

    DEPRECATED - will be removed along with mongodb.

    Args:
         project (object): django project
    """
    base_project = BaseProject.objects.get(project_id=project.deprecated_project_id)
    return get_project_datastore(base_project).project_collection_is_loaded(base_project)
