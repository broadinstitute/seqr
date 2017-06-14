"""
APIs used by the project page
"""

import itertools
import json
import logging

from guardian.shortcuts import get_objects_for_group
from django.contrib.auth.decorators import login_required
from django.db import connection

from seqr.models import Project, Family, Individual, Sample, _slugify, CAN_EDIT, CAN_VIEW, LocusList, \
    LocusListEntry, VariantTagType, VariantTag
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.export_table_utils import export_individuals, export_families
from seqr.views.utils.json_utils import render_with_initial_json, create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user, _get_json_for_project


from seqr.views.utils.sql_to_json_utils import _get_json_for_sample_fields, _get_json_for_sample_batch_fields, \
    _get_json_for_individual_fields, _get_json_for_family_fields

from seqr.views.utils.request_utils import _get_project_and_check_permissions
from xbrowse_server.mall import get_project_datastore

logger = logging.getLogger(__name__)


@login_required
def project_page(request, project_guid):
    """Generates the project page, with initial project_page_data json embedded."""

    initial_json = json.loads(
        project_page_data(request, project_guid).content
    )

    return render_with_initial_json('project_page.html', initial_json)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def project_page_data(request, project_guid):
    """Returns a JSON object containing information used by the project page:
    ::

      json_response = {
         'user': {..},
         'familiesByGuid': {..},
         'individualsByGuid': {..},
         'samplesByGuid': {..},
         'sampleBatchesByGuid': {..},
       }

    Args:
        project_guid (string): GUID of the Project to retrieve data for.
    """

    project = _get_project_and_check_permissions(project_guid, request.user)

    cursor = connection.cursor()

    families_by_guid, individuals_by_guid = _retrieve_families_and_individuals(cursor, project.guid)
    samples_by_guid, sample_batches_by_guid = _retrieve_samples(cursor, project.guid, individuals_by_guid)

    cursor.close()

    project_json = _get_json_for_project(project, request.user)
    project_json['collaborators'] = _get_json_for_collaborator_list(project)
    project_json['geneLists'] = _get_json_for_gene_lists(project)
    project_json['variantTagTypes'] = _get_json_for_variant_tag_types(project)
    #project_json['referencePopulations'] = _get_json_for_reference_populations(project)

    # gene search will be deprecated once the new database is online.
    project_json['hasGeneSearch'] = _has_gene_search(project)

    user_json = _get_json_for_user(request.user)
    user_json['hasEditPermissions'] = request.user.is_staff or request.user.has_perm(CAN_EDIT, project)
    user_json['hasViewPermissions'] = user_json['hasEditPermissions'] or request.user.has_perm(CAN_VIEW, project)

    json_response = {
        'user': user_json,
        'project': project_json,
        'familiesByGuid': families_by_guid,
        'individualsByGuid': individuals_by_guid,
        'samplesByGuid': samples_by_guid,
        'sampleBatchesByGuid': sample_batches_by_guid,
    }

    return create_json_response(json_response)


def _retrieve_families_and_individuals(cursor, project_guid):
    """Retrieves family- and individual-level metadata for the given project.

    Args:
        cursor: connected database cursor that can be used to execute SQL queries.
        project_guid (string): project_guid
    Returns:
        2-tuple with dictionaries: (families_by_guid, individuals_by_guid)
    """

    families_query = """
        SELECT DISTINCT
          f.guid AS family_guid,
          f.family_id AS family_id,
          f.display_name AS family_display_name,
          f.description AS family_description,
          f.analysis_notes AS family_analysis_notes,
          f.analysis_summary AS family_analysis_summary,
          f.pedigree_image AS family_pedigree_image,
          f.analysis_status AS family_analysis_status,
          f.causal_inheritance_mode AS family_causal_inheritance_mode,
          f.internal_analysis_status AS family_internal_analysis_status,
          f.internal_case_review_notes AS family_internal_case_review_notes,
          f.internal_case_review_summary AS family_internal_case_review_summary,

          i.guid AS individual_guid,
          i.individual_id AS individual_id,
          i.display_name AS individual_display_name,
          i.paternal_id AS individual_paternal_id,
          i.maternal_id AS individual_maternal_id,
          i.sex AS individual_sex,
          i.affected AS individual_affected,
          i.notes as individual_notes,
          i.case_review_status AS individual_case_review_status,
          i.case_review_status_accepted_for AS individual_case_review_status_accepted_for,
          i.case_review_status_last_modified_date AS individual_case_review_status_last_modified_date,
          i.case_review_status_last_modified_by_id AS individual_case_review_status_last_modified_by,
          i.case_review_discussion AS individual_case_review_discussion,
          i.phenotips_patient_id AS individual_phenotips_patient_id,
          i.phenotips_data AS individual_phenotips_data,
          i.created_date AS individual_created_date,
          i.last_modified_date AS individual_last_modified_date

        FROM seqr_project AS p
          JOIN seqr_family AS f ON f.project_id=p.id
          JOIN seqr_individual AS i ON i.family_id=f.id
        WHERE p.guid=%s
    """.strip()

    cursor.execute(families_query, [project_guid])

    columns = [col[0] for col in cursor.description]

    families_by_guid = {}
    individuals_by_guid = {}
    for row in cursor.fetchall():
        record = dict(zip(columns, row))

        family_guid = record['family_guid']
        if family_guid not in families_by_guid:
            families_by_guid[family_guid] = _get_json_for_family_fields(record)
            families_by_guid[family_guid]['individualGuids'] = []

        individual_guid = record['individual_guid']
        if individual_guid not in individuals_by_guid:
            individuals_by_guid[individual_guid] = _get_json_for_individual_fields(record)
            phenotips_data = individuals_by_guid[individual_guid]['phenotipsData']
            if phenotips_data:
                try:
                    individuals_by_guid[individual_guid]['phenotipsData'] = json.loads(phenotips_data)
                except Exception as e:
                    logger.error("Couldn't parse phenotips: %s", e)
            individuals_by_guid[individual_guid]['sampleGuids'] = []

            families_by_guid[family_guid]['individualGuids'].append(individual_guid)


    return families_by_guid, individuals_by_guid


def _retrieve_samples(cursor, project_guid, individuals_by_guid):
    """Retrieves sample-batch- and sample-level metadata for the given project.

        Args:
            cursor: connected database cursor that can be used to execute SQL queries.
            project_guid (string): project_guid
        Returns:
            2-tuple with dictionaries: (samples_by_guid, sample_batches_by_guid)
        """

    # use raw SQL since the Django ORM doesn't have a good way to express these types of queries.
    sample_batch_query = """
        SELECT DISTINCT
          sb.guid AS sample_batch_guid,
          sb.name AS sample_batch_name,
          sb.description AS sample_batch_description,
          sb.sample_type AS sample_batch_sample_type,
          sb.genome_build_id AS sample_batch_genome_build_id,

          s.guid AS sample_guid,
          s.sample_id AS sample_id,
          s.sample_status AS sample_status,
          s.is_loaded AS sample_is_loaded,
          s.loaded_date AS sample_loaded_date,
          s.source_file_path AS sample_source_file_path,
          s.created_date AS sample_created_date,
          s.last_modified_date AS sample_last_modified_date,

          i.guid AS individual_guid

        FROM seqr_samplebatch AS sb
          JOIN seqr_sample AS s ON sb.id=s.sample_batch_id
          JOIN seqr_individual_samples AS iss ON iss.sample_id=s.id
          JOIN seqr_individual AS i ON iss.individual_id=i.id
          JOIN seqr_family AS f ON i.family_id=f.id
          JOIN seqr_project AS p ON f.project_id=p.id
        WHERE p.guid=%s
    """.strip()

    cursor.execute(sample_batch_query, [project_guid])

    columns = [col[0] for col in cursor.description]

    samples_by_guid = {}
    sample_batches_by_guid = {}
    for row in cursor.fetchall():
        record = dict(zip(columns, row))

        individual_guid = record['individual_guid']
        sample_batch_guid = record['sample_batch_guid']
        if sample_batch_guid not in sample_batches_by_guid:
            sample_batches_by_guid[sample_batch_guid] = _get_json_for_sample_batch_fields(record)
            sample_batches_by_guid[sample_batch_guid]['sampleGuids'] = []

        sample_guid = record['sample_guid']
        samples_by_guid[sample_guid] = _get_json_for_sample_fields(record)
        samples_by_guid[sample_guid]['sampleBatchGuid'] = sample_batch_guid
        samples_by_guid[sample_guid]['individualGuid'] = individual_guid

        sample_batches_by_guid[sample_batch_guid]['sampleGuids'].append(sample_guid)
        individuals_by_guid[individual_guid]['sampleGuids'].append(sample_guid)

    return samples_by_guid, sample_batches_by_guid


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


def _get_json_for_gene_lists(project):
    result = []

    for locus_list in get_objects_for_group(project.can_view_group, CAN_VIEW, LocusList):
        result.append({
            'locusListGuid': locus_list.guid,
            'createdDate': locus_list.created_date,
            'name': locus_list.name,
            'deprecatedGeneListId': _slugify(locus_list.name),
            'description': locus_list.description,
            'numEntries': LocusListEntry.objects.filter(parent=locus_list).count(),
        })

    return sorted(result, key=lambda locus_list: locus_list['createdDate'])


def _get_json_for_variant_tag_types(project):
    result = []

    for variant_tag_type in VariantTagType.objects.filter(project=project):
        result.append({
            'name': variant_tag_type.name,
            'category': variant_tag_type.category,
            'description': variant_tag_type.description,
            'color': variant_tag_type.color,
            'order': variant_tag_type.order,
            'is_built_in': variant_tag_type.is_built_in,
            'numTags': VariantTag.objects.filter(variant_tag_type=variant_tag_type).count(),
        })

    return sorted(result, key=lambda variant_tag_type: variant_tag_type['order'])


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
def export_project_families(request, project_guid):
    """Export project Families table.

    Args:
        project_guid (string): GUID of the project for which to export family data
    """
    format = request.GET.get('file_format', 'tsv')

    project = _get_project_and_check_permissions(project_guid, request.user)

    # get all families in this project
    families = Family.objects.filter(project=project).order_by('family_id')

    filename_prefix = "%s_families" % _slugify(project.name)

    return export_families(filename_prefix, families, format, include_case_review_columns=False)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def export_project_individuals(request, project_guid):
    """Export project Individuals table.

    Args:
        project_guid (string): GUID of the project for which to export individual data
    """

    format = request.GET.get('file_format', 'tsv')
    include_phenotypes = bool(request.GET.get('include_phenotypes'))

    project = _get_project_and_check_permissions(project_guid, request.user)

    # get all individuals in this project
    individuals = Individual.objects.filter(family__project=project).order_by('family__family_id', 'affected')

    filename_prefix = "%s_individuals" % _slugify(project.name)

    return export_individuals(filename_prefix, individuals, format, include_phenotips_columns=include_phenotypes)


def _has_gene_search(project):
    """
    Returns True if this project has Gene Search enabled.

    DEPRECATED - will be removed along with mongodb.

    Args:
         project (object): django project
    """
    return get_project_datastore(
        project.deprecated_project_id).project_collection_is_loaded(project.deprecated_project_id)
