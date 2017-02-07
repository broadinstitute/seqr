import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import connection

from seqr.views.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils import \
    _get_json_for_user, \
    render_with_initial_json, \
    create_json_response
from seqr.models import Project, ProjectCategory

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
    """Returns a JSON object containing information used by the case review page:
    ::

      json_response = {
         'user': {..},
         'familiesByGuid': {..},
         'individualsByGuid': {..},
         'familyGuidToIndivGuids': {..},
       }
    Args:
        project_guid (string): GUID of the Project under case review.
    """

    # get all projects this user has permissions to view
    if request.user.is_staff:
        projects = projects_user_can_edit = Project.objects.all()
        projects_WHERE_clause = ''
    else:
        projects = Project.objects.filter(can_view_group__user=request.user)
        projects_WHERE_clause = 'WHERE p.guid in (%s)' % (','.join("'%s'" % p.guid for p in projects))
        projects_user_can_edit = Project.objects.filter(can_edit_group__user=request.user)

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

    cursor = connection.cursor()
    cursor.execute(projects_query)

    key_map = {'deprecated_last_accessed_date': 'last_accessed_date'}
    columns = [_to_camel_case(_remap_key(col[0], key_map)) for col in cursor.description]

    projects_by_guid = {
        r['projectGuid']: r for r in (dict(zip(columns, row)) for row in cursor.fetchall())
    }


    # retrieve solve counts for each project
    ANALYSIS_STATUS_CATEGORIES = {
        'S':       'Solved',
        'S_kgfp':  'Solved',
        'S_kgdp':  'solved',
        'S_ng':    'Solved',
        'Sc_kgfp': 'Strong candidate',
        'Sc_kgdp': 'Strong candidate',
        'Sc_ng':   'Strong candidate',
        'Rncc':    'Reviewed, no candidate',
        'Rcpc':    'Analysis in progress',
        'I':       'Analysis in progress',
        'Q':       'Waiting for data',
    }


    analysis_status_query = """
      SELECT
        p.guid AS project_guid,
        f.analysis_status AS analysis_status,
        count(*) as analysis_status_count
      FROM seqr_family AS f
      JOIN seqr_project AS p
       ON f.project_id = p.id
      GROUP BY p.guid, f.analysis_status
    """.strip() % locals()

    cursor.execute(analysis_status_query)

    columns = [col[0] for col in cursor.description]
    for row in cursor.fetchall():
        analysis_status_record = dict(zip(columns, row))
        project_guid = analysis_status_record['project_guid']
        analysis_status_count = analysis_status_record['analysis_status_count']
        analysis_status_category = ANALYSIS_STATUS_CATEGORIES[analysis_status_record['analysis_status']]

        if 'analysisStatusCounts' not in projects_by_guid[project_guid]:
            projects_by_guid[project_guid]['analysisStatusCounts'] = {}
        analysis_status_counts_dict = projects_by_guid[project_guid]['analysisStatusCounts']

        analysis_status_counts_dict[analysis_status_category] = analysis_status_counts_dict.get(analysis_status_category, 0) + analysis_status_count

    # retrieve all project categories
    for project_guid in projects_by_guid:
        projects_by_guid[project_guid]['projectCategoryGuids'] = []

    project_categories_by_guid = {}
    for project_category in ProjectCategory.objects.all():
        project_category_guid = project_category.guid

        for p in project_category.projects.all():
            projects_by_guid[p.guid]['projectCategoryGuids'].append(project_category_guid)

        project_categories_by_guid[project_category_guid] = project_category.json()

    # do a separate query to get details on all datasets in these projects
    num_samples_subquery = """
      SELECT COUNT(*) FROM seqr_sequencingsample AS subquery_s
        WHERE subquery_s.dataset_id=d.id
    """
    datasets_query = """
        SELECT
          p.guid AS project_guid,
          d.guid AS dataset_guid,
          d.sequencing_type AS sequencing_type,
          d.is_loaded AS is_loaded,
          (%(num_samples_subquery)s) AS num_samples
        FROM seqr_dataset AS d
          JOIN seqr_sequencingsample AS s ON d.id=s.dataset_id
          JOIN seqr_individual_sequencing_samples AS iss ON iss.sequencingsample_id=s.id
          JOIN seqr_individual AS i ON iss.individual_id=i.id
          JOIN seqr_family AS f ON i.family_id=f.id
          JOIN seqr_project AS p ON f.project_id=p.id %(projects_WHERE_clause)s
        GROUP BY p.guid, d.id, d.sequencing_type, d.is_loaded
    """.strip() % locals()

    cursor.execute(datasets_query)


    columns = [_to_camel_case(col[0]) for col in cursor.description]
    datasets_by_guid = {}
    for row in cursor.fetchall():
        dataset_project_record = dict(zip(columns, row))
        project_guid = dataset_project_record['projectGuid']
        dataset_guid = dataset_project_record['datasetGuid']
        del dataset_project_record['projectGuid']
        del dataset_project_record['datasetGuid']

        project_record = projects_by_guid[project_guid]
        if 'datasets' not in project_record:
            project_record['datasetGuids'] = []
        project_record['datasetGuids'].append(dataset_guid)

        datasets_by_guid[dataset_guid] = dataset_project_record

    cursor.close()

    # mark all projects where this user has edit permissions
    for project in projects_user_can_edit:
        projects_by_guid[project.guid]['canEdit'] = True

    json_response = {
        'user': _get_json_for_user(request.user),
        'projectsByGuid': projects_by_guid,
        'projectCategoriesByGuid': project_categories_by_guid,
        'datasetsByGuid': datasets_by_guid,
    }

    return create_json_response(json_response)


def _remap_key(key, key_map):
    return key_map.get(key, key)


def _to_camel_case(snake_case_str):
    components = snake_case_str.split('_')
    return components[0] + "".join(x.title() for x in components[1:])
