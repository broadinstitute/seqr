import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import connection

from seqr.views.auth_api import API_LOGIN_REDIRECT_URL
from seqr.views.utils import \
    _get_json_for_user, \
    _get_json_for_project, \
    render_with_initial_json, \
    create_json_response
from seqr.models import Project, Family, Individual

logger = logging.getLogger(__name__)


@login_required
def dashboard_page(request):
    """Generates the dashboard page, with initial dashboard_page_data json embedded."""

    initial_json = json.loads(
        dashboard_page_data(request).content
    )

    return render_with_initial_json('dashboard.html', initial_json)


@login_required(login_url=API_LOGIN_REDIRECT_URL)
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
        projects = Project.objects.all()
        projects_WHERE_clause = ''
    else:
        projects = Project.objects.filter(can_view_group__user=request.user)
        projects_WHERE_clause = 'WHERE p.guid in (%s)' % (','.join("'%s'" % p.guid for p in projects))

    project_table = Project._meta.db_table
    family_table = Family._meta.db_table
    individual_table = Individual._meta.db_table

    cursor = connection.cursor()
    query = """
      SELECT
        *,
        (SELECT count(*) FROM %(family_table)s WHERE project_id=p.id) AS num_families,
        (SELECT count(*) FROM %(individual_table)s as i JOIN seqr_family as f on i.family_id=f.id WHERE f.project_id=p.id) AS num_individuals
      FROM %(project_table)s as p %(projects_WHERE_clause)s
    """ % locals()
    cursor.execute(query.strip())

    print("QUERY: %s" %(query))
    columns = [to_camel_case(col[0]).replace('guid', 'projectGuid') for col in cursor.description]
    projects_by_guid = {
        project_record['projectGuid']:
            project_record for project_record in (dict(zip(columns, row)) for row in cursor.fetchall())
    }
    cursor.close()

    # TODO  - awesome bar search
    # TODO - tests, readme how to add SVs,
    print("QUERIES: " + str(connection.queries))
    """
        'can_edit_group_id': 467,
        'can_view_group_id': 468,
        'created_by_id': None,
        'created_date': datetime.datetime(2017, 1, 6, 16, 22, 1, 506425, tzinfo=<UTC>),
        'deprecated_project_id': u'manton_orphan-diseases_cmg-samples_genomes_v1',
        'description': u'',
        'displayName': u'Manton - Orphan Diseases - CMG - Genomes',
        'id': 156,
        'is_mme_enabled': False,
        'is_phenotips_enabled': True,
        'last_modified_date': datetime.datetime(2017, 1, 6, 16, 22, 1, 540608, tzinfo=<UTC>),
        'mme_primary_data_owner': None,
        'num_families': 7L,
        'num_individuals': 23L,
        'owners_group_id': 466,
        'phenotips_user_id': u'manton_orphan-diseases_cmg-samples_genomes_v1',
        'projectGuid': u'R0156_manton_orphan_diseases_c',
        'project_category': None
    'projectGuid': project.guid,
    'displayName': project.name,
    'description': project.description,
    'created_date': project.created_date,
    'last_modified_date': project.last_modified_date,
    'deprecatedProjectId': project.deprecated_project_id,
    'category': project.project_category,
    'is_phenotips_enabled': project.is_phenotips_enabled,
    'phenotips_user_id': project.phenotips_user_id,
    'is_mme_enabled': project.is_mme_enabled,
    'mme_primary_data_owner': project.mme_primary_data_owner,
    """

    json_response = {
        'user': _get_json_for_user(request.user),
        'projectsByGuid': projects_by_guid,
    }

    from pprint import pprint
    pprint(json_response)

    #for p in projects:
    #    json_response['projectsByGuid'][p.guid]['num_families'] = p.family_set.all().count()

    return create_json_response(json_response)


def to_camel_case(snake_case_str):
    components = snake_case_str.split('_')
    return components[0] + "".join(x.title() for x in components[1:])