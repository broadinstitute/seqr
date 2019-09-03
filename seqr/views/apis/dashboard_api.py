"""
APIs used by the main seqr dashboard page
"""

import logging

from django.db import connection, models
from django.contrib.auth.decorators import login_required

from seqr.models import ProjectCategory, Sample, Family
from seqr.views.utils.export_table_utils import export_table
from seqr.views.utils.json_utils import create_json_response, _to_camel_case
from seqr.views.utils.orm_to_json_utils import get_json_for_projects
from seqr.views.utils.permissions_utils import get_projects_user_can_view
from settings import API_LOGIN_REQUIRED_URL

logger = logging.getLogger(__name__)


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

    # TODO get rid of raw SQL execution
    cursor = connection.cursor()

    projects_by_guid = _get_projects_json(request.user, cursor)

    project_categories_by_guid = _retrieve_project_categories_by_guid(projects_by_guid.keys())

    cursor.close()

    json_response = {
        'projectsByGuid': projects_by_guid,
        'projectCategoriesByGuid': project_categories_by_guid,
    }

    return create_json_response(json_response)


def _get_projects_json(user, cursor):
    projects = get_projects_user_can_view(user)
    projects_with_counts = projects.annotate(
        models.Count('family', distinct=True), models.Count('family__individual', distinct=True),
        models.Count('family__savedvariant', distinct=True))

    projects_by_guid = {p['projectGuid']: p for p in get_json_for_projects(projects, user=user)}
    for project in projects_with_counts:
        projects_by_guid[project.guid]['numFamilies'] = project.family__count
        projects_by_guid[project.guid]['numIndividuals'] = project.family__individual__count
        projects_by_guid[project.guid]['numVariantTags'] = project.family__savedvariant__count

    #  TODO get rid of cursor
    _add_analysis_status_counts(cursor, projects_by_guid)
    _add_sample_type_counts(cursor, projects_by_guid)

    return projects_by_guid


def _to_WHERE_clause(project_guids):
    """Converts a list of project GUIDs to a SQL WHERE clause"""
    if len(project_guids) == 0:
        return 'WHERE 1=2'  # defensive programming

    return 'WHERE p.guid in (%s)' % (','.join("'%s'" % guid for guid in project_guids))


def _retrieve_project_categories_by_guid(project_guids):
    """Retrieves project categories from the database, and returns a 'project_categories_by_guid' dictionary,
    while also adding a 'projectCategoryGuids' attribute to each project dict in 'projects_by_guid'.

    Args:
        projects_by_guid: Dictionary that maps each project's GUID to a dictionary of key-value
            pairs representing attributes of that project.

    Returns:
        Dictionary that maps each category's GUID to a dictionary of key-value pairs representing
        attributes of that category.
    """
    if len(project_guids) == 0:
        return {}

    # retrieve all project categories
    project_categories = ProjectCategory.objects.filter(projects__guid__in=project_guids).distinct()

    project_categories_by_guid = {}
    for project_category in project_categories:
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
    else:
        projects_WHERE_clause = _to_WHERE_clause([project_guid for project_guid in projects_by_guid])

    analysis_status_counts_query = """
      SELECT
        p.guid AS project_guid,
        f.analysis_status AS analysis_status,
        COUNT(*) as analysis_status_count
      FROM seqr_family AS f
      JOIN seqr_project AS p
       ON f.project_id = p.id
      %(projects_WHERE_clause)s
      GROUP BY p.guid, f.analysis_status
    """.strip() % locals()

    cursor.execute(analysis_status_counts_query)

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

        projects_by_guid[project_guid]['analysisStatusCounts'][analysis_status_name] = analysis_status_count


def _add_sample_type_counts(cursor, projects_by_guid):
    """Retrieves per-family analysis status counts from the database and adds these to each project
    in the 'projects_by_guid' dictionary.

    Args:
        cursor: connected database cursor that can be used to execute SQL queries.
        projects_by_guid (dict): projects for which to add analysis counts
    """

    if len(projects_by_guid) == 0:
        return {}

    sample_type_counts_query = """
        SELECT
          p.guid AS project_guid,
          s.sample_type AS sample_type,
          COUNT(distinct s.individual_id) AS num_samples
        FROM seqr_sample AS s
          JOIN seqr_individual AS i ON s.individual_id=i.id
          JOIN seqr_family AS f ON i.family_id=f.id
          JOIN seqr_project AS p ON f.project_id=p.id
        {projects_WHERE_clause}
        AND dataset_type='{variant_dataset_type}'
        AND sample_status='{loaded_sample_status}'
        GROUP BY p.guid, s.sample_type
    """.strip().format(
        projects_WHERE_clause=_to_WHERE_clause([guid for guid in projects_by_guid]),
        variant_dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        loaded_sample_status=Sample.SAMPLE_STATUS_LOADED,
    )

    cursor.execute(sample_type_counts_query)

    columns = [_to_camel_case(col[0]) for col in cursor.description]
    for row in cursor.fetchall():
        record = dict(zip(columns, row))
        project_guid = record['projectGuid']
        sample_type = record['sampleType']
        num_samples = record['numSamples']

        if project_guid not in projects_by_guid:
            continue  # defensive programming

        if 'sampleTypeCounts' not in projects_by_guid[project_guid]:
            projects_by_guid[project_guid]['sampleTypeCounts'] = {}

        projects_by_guid[project_guid]['sampleTypeCounts'][sample_type] = num_samples


@login_required
def export_projects_table_handler(request):
    file_format = request.GET.get('file_format', 'tsv')

    cursor = connection.cursor()

    projects_by_guid = _get_projects_json(request.user, cursor)
    project_categories_by_guid = _retrieve_project_categories_by_guid(projects_by_guid.keys())

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
    for project in sorted(projects_by_guid.values(), key=lambda project: project.get('name') or project.get('deprecatedProjectId')):
        project_categories = ', '.join(
            [project_categories_by_guid[category_guid]['name'] for category_guid in project.get('projectCategoryGuids')]
        )

        row = [
            project.get('name') or project.get('deprecatedProjectId'),
            project.get('description'),
            project_categories,
            project.get('createdDate'),
            project.get('numFamilies'),
            project.get('numIndividuals'),
            project.get('numVariantTags'),
            project.get('sampleTypeCounts', {}).get(Sample.SAMPLE_TYPE_WES, 0),
            project.get('sampleTypeCounts', {}).get(Sample.SAMPLE_TYPE_WGS, 0),
            project.get('sampleTypeCounts', {}).get(Sample.SAMPLE_TYPE_RNA, 0),
        ]

        row.extend([project.get('analysisStatusCounts', {}).get(key, 0) for key, _ in Family.ANALYSIS_STATUS_CHOICES if key != 'S'])

        rows.append(row)

    return export_table('projects', header, rows, file_format)
