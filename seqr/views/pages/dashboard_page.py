"""
APIs used by the main seqr dashboard page
"""

import json
import logging

from django.db import connection
from django.contrib.auth.decorators import login_required

from seqr.models import Project, ProjectCategory, SampleBatch, Family
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.export_table_utils import export_table
from seqr.views.utils.json_utils import render_with_initial_json, create_json_response, _to_camel_case
from seqr.views.utils.orm_to_json_utils import _get_json_for_user

logger = logging.getLogger(__name__)


@login_required
def dashboard_page(request):
    """Generates the dashboard page, with initial dashboard_page_data json embedded."""

    initial_json = json.loads(
        dashboard_page_data(request).content
    )

    return render_with_initial_json('dashboard.html', initial_json)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def dashboard_page_data(request):
    """Returns a JSON object containing information used by the dashboard page:
    ::

      json_response = {
         'user': {..},
         'familiesByGuid': {..},
         'individualsByGuid': {..},
       }
    """

    cursor = connection.cursor()

    if request.user.is_staff:
        projects_user_can_view = projects_user_can_edit = Project.objects.all()
    else:
        projects_user_can_view = Project.objects.filter(can_view_group__user=request.user)
        projects_user_can_edit = Project.objects.filter(can_edit_group__user=request.user)

        # defensive programming
        edit_but_not_view_permissions = set(p.guid for p in projects_user_can_edit) - set(p.guid for p in projects_user_can_view)
        if edit_but_not_view_permissions:
            raise Exception('ERROR: %s has EDIT permissions but not VIEW permissions for: %s' % (request.user, edit_but_not_view_permissions))

    projects_by_guid = _retrieve_projects_by_guid(cursor, projects_user_can_view, projects_user_can_edit)

    _add_analysis_status_counts(cursor, projects_by_guid)

    project_categories_by_guid = _retrieve_project_categories_by_guid(projects_by_guid)

    sample_batches_by_guid = _retrieve_sample_batches_by_guid(cursor, projects_by_guid)

    cursor.close()

    json_response = {
        'user': _get_json_for_user(request.user),
        'projectsByGuid': projects_by_guid,
        'projectCategoriesByGuid': project_categories_by_guid,
        'sampleBatchesByGuid': sample_batches_by_guid,
    }

    return create_json_response(json_response)


def _to_WHERE_clause(project_guids):
    """Converts a list of project GUIDs to a SQL WHERE clause"""
    if len(project_guids) == 0:
        return 'WHERE 1=2'  # defensive programming

    return 'WHERE p.guid in (%s)' % (','.join("'%s'" % guid for guid in project_guids))

def _retrieve_projects_by_guid(cursor, projects_user_can_view, projects_user_can_edit):
    """Retrieves all relevant metadata for each project from the database, and returns a 'projects_by_guid' dictionary.

    Args:
        cursor: connected database cursor that can be used to execute SQL queries.
        projects_user_can_view (list): list of Django Project objects for which the user has CAN_VIEW permissions.
        projects_user_can_edit (list): list of Django Project objects for which the user has CAN_EDIT permissions.
    Returns:
        Dictionary that maps each project's GUID to a dictionary of key-value pairs representing
        attributes of that project.
    """

    if len(projects_user_can_view) == 0:
        return {}

    # get all projects this user has permissions to view
    projects_WHERE_clause = _to_WHERE_clause([p.guid for p in projects_user_can_view])

    # use raw SQL to avoid making N+1 queries.
    num_families_subquery = """
      SELECT count(*) FROM seqr_family
        WHERE project_id=p.id
    """.strip()

    num_variant_tags_subquery = """
      SELECT count(*) FROM seqr_varianttag AS v
        JOIN seqr_varianttagtype AS t ON v.variant_tag_type_id=t.id
        WHERE project_id=p.id
    """.strip()

    num_individuals_subquery = """
      SELECT count(*) FROM seqr_individual AS i
        JOIN seqr_family AS f ON i.family_id=f.id
        WHERE f.project_id=p.id
    """.strip()

    projects_query = """
      SELECT
        guid AS project_guid,
        p.name AS name,
        description,
        deprecated_project_id,
        created_date,
        deprecated_last_accessed_date,
        (%(num_variant_tags_subquery)s) AS num_variant_tags,
        (%(num_families_subquery)s) AS num_families,
        (%(num_individuals_subquery)s) AS num_individuals
      FROM seqr_project AS p
      %(projects_WHERE_clause)s
    """.strip() % locals()

    cursor.execute(projects_query)

    columns = [_to_camel_case(col[0]) for col in cursor.description]

    projects_by_guid = {
        r['projectGuid']: r for r in (dict(zip(columns, row)) for row in cursor.fetchall())
    }

    # mark all projects where this user has edit permissions
    for project in projects_user_can_edit:
        projects_by_guid[project.guid]['canEdit'] = True

    return projects_by_guid

def _retrieve_project_categories_by_guid(projects_by_guid):
    """Retrieves project categories from the database, and returns a 'project_categories_by_guid' dictionary,
    while also adding a 'projectCategoryGuids' attribute to each project dict in 'projects_by_guid'.

    Args:
        projects_by_guid: Dictionary that maps each project's GUID to a dictionary of key-value
            pairs representing attributes of that project.

    Returns:
        Dictionary that maps each category's GUID to a dictionary of key-value pairs representing
        attributes of that category.
    """
    if len(projects_by_guid) == 0:
        return {}

    project_guids = [guid for guid in projects_by_guid]
    # retrieve all project categories
    for project_guid in projects_by_guid:
        projects_by_guid[project_guid]['projectCategoryGuids'] = []

    project_categories_by_guid = {}
    for project_category in ProjectCategory.objects.filter(projects__guid__in=project_guids).distinct():
        for p in project_category.projects.filter(guid__in=project_guids):
            projects_by_guid[p.guid]['projectCategoryGuids'].append(project_category.guid)

        project_categories_by_guid[project_category.guid] = project_category.json()

    return project_categories_by_guid


def _add_analysis_status_counts(cursor, projects_by_guid):
    """Retrieves per-family analysis status counts from the database and adds these to each project
    in the 'projects_by_guid' dictionary.

    Args:
        cursor: connected database cursor that can be used to execute SQL queries.
        projects_by_guid (dict): projects for which to add analysis counts
    """

    if len(projects_by_guid) == 0:
        return

    projects_WHERE_clause = _to_WHERE_clause([project_guid for project_guid in projects_by_guid])

    analysis_status_query = """
      SELECT
        p.guid AS project_guid,
        f.analysis_status AS analysis_status,
        count(*) as analysis_status_count
      FROM seqr_family AS f
      JOIN seqr_project AS p
       ON f.project_id = p.id
      %(projects_WHERE_clause)s
      GROUP BY p.guid, f.analysis_status
    """.strip() % locals()

    cursor.execute(analysis_status_query)

    columns = [col[0] for col in cursor.description]
    for row in cursor.fetchall():
        analysis_status_record = dict(zip(columns, row))
        project_guid = analysis_status_record['project_guid']
        analysis_status_count = analysis_status_record['analysis_status_count']
        analysis_status_name = analysis_status_record['analysis_status']

        if project_guid not in projects_by_guid:
            continue  # defensive programming

        if 'analysisStatusCounts' not in projects_by_guid[project_guid]:
            projects_by_guid[project_guid]['analysisStatusCounts'] = {}
        analysis_status_counts_dict = projects_by_guid[project_guid]['analysisStatusCounts']

        analysis_status_counts_dict[analysis_status_name] = analysis_status_count


def _retrieve_sample_batches_by_guid(cursor, projects_by_guid):
    """Retrieves sample batches from the database, and returns a 'sample_batches_by_guid' dictionary,
    while also adding a 'sampleBatchGuids' attribute to each project dict in 'projects_by_guid'

    Args:
        cursor: connected database cursor that can be used to execute SQL queries.
        projects_by_guid: Dictionary that maps each project's GUID to a dictionary of key-value pairs
            representing attributes of that project.

    Returns:
        Dictionary that maps each sample batch's GUID to a dictionary of key-value pairs representing
        attributes of this sample batch.
    """
    if len(projects_by_guid) == 0:
        return {}

    projects_WHERE_clause = _to_WHERE_clause([guid for guid in projects_by_guid])

    num_samples_subquery = """
      SELECT COUNT(*) FROM seqr_sample AS subquery_s
        WHERE subquery_s.sample_batch_id=sb.id
    """
    sample_batch_query = """
        SELECT
          p.guid AS project_guid,
          sb.guid AS sample_batch_guid,
          sb.id AS sample_batch_id,
          sb.sample_type AS sample_type,
          (%(num_samples_subquery)s) AS num_samples
        FROM seqr_samplebatch AS sb
          JOIN seqr_sample AS s ON sb.id=s.sample_batch_id
          JOIN seqr_individual_samples AS iss ON iss.sample_id=s.id
          JOIN seqr_individual AS i ON iss.individual_id=i.id
          JOIN seqr_family AS f ON i.family_id=f.id
          JOIN seqr_project AS p ON f.project_id=p.id
        %(projects_WHERE_clause)s
        GROUP BY p.guid, sb.guid, sb.id, sb.sample_type
    """.strip() % locals()

    # TODO retrieve sample batches based on sample batch permissions instead of going by project permissions

    cursor.execute(sample_batch_query)

    columns = [_to_camel_case(col[0]) for col in cursor.description]
    sample_batches_by_guid = {}
    for row in cursor.fetchall():
        sample_batch_project_record = dict(zip(columns, row))
        sample_batch_guid = sample_batch_project_record['sampleBatchGuid']

        project_guid = sample_batch_project_record['projectGuid']

        del sample_batch_project_record['projectGuid']
        #del sample_batch_project_record['sampleBatchGuid']

        sample_batches_by_guid[sample_batch_guid] = sample_batch_project_record

        project_record = projects_by_guid[project_guid]
        if 'sampleBatchGuids' not in project_record:
            project_record['sampleBatchGuids'] = []
        project_record['sampleBatchGuids'].append(sample_batch_guid)

    return sample_batches_by_guid


@login_required
def export_projects_table(request):
    file_format = request.GET.get('file_format', 'tsv')

    cursor = connection.cursor()

    if request.user.is_staff:
        projects_user_can_view = Project.objects.all()
    else:
        projects_user_can_view = Project.objects.filter(can_view_group__user=request.user)

    projects_by_guid = _retrieve_projects_by_guid(cursor, projects_user_can_view, [])
    _add_analysis_status_counts(cursor, projects_by_guid)
    sample_batches_by_guid = _retrieve_sample_batches_by_guid(cursor, projects_by_guid)
    project_categories_by_guid = _retrieve_project_categories_by_guid(projects_by_guid)

    cursor.close()

    header = [
        'Project',
        'Description',
        'Categories',
        'Created Date',
        'Families',
        'Individuals',
        'Tagged Variants',
        'WES Samples',
        'WGS Samples',
        'RNA Samples',
    ]

    header.extend([label for key, label in Family.ANALYSIS_STATUS_CHOICES if key != 'S'])

    rows = []
    for _, proj in sorted(projects_by_guid.items(), key=lambda item: item[1].get('name') or item[1].get('deprecatedProjectId')):
        project_categories = ', '.join(
            [project_categories_by_guid[category_guid]['name'] for category_guid in proj.get('projectCategoryGuids')]
        )

        num_samples_by_sequecing_type = {}
        for sample_batch_guid in proj.get('sampleBatchGuids', []):
            sample_batch = sample_batches_by_guid[sample_batch_guid]
            num_samples_by_sequecing_type[sample_batch['sampleType']] = sample_batch['numSamples']

        row = [
            proj.get('name') or proj.get('deprecatedProjectId'),
            proj.get('description'),
            project_categories,
            proj.get('createdDate'),
            proj.get('numFamilies'),
            proj.get('numIndividuals'),
            proj.get('numVariantTags'),
            num_samples_by_sequecing_type.get(SampleBatch.SAMPLE_TYPE_WES, 0),
            num_samples_by_sequecing_type.get(SampleBatch.SAMPLE_TYPE_WGS, 0),
            num_samples_by_sequecing_type.get(SampleBatch.SAMPLE_TYPE_RNA, 0),
        ]

        row.extend([proj.get('analysisStatusCounts', {}).get(key, 0) for key, _ in Family.ANALYSIS_STATUS_CHOICES if key != 'S'])

        rows.append(row)

    return export_table('projects', header, rows, file_format)
