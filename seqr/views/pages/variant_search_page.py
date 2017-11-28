import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import render_with_initial_json, create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user, _get_json_for_project
from seqr.models import Project, CAN_VIEW, Sample, Dataset, Family
from seqr.views.utils.request_utils import _get_project_and_check_permissions
from seqr.views.utils.sql_to_json_utils import _get_json_for_family_fields, _get_json_for_individual_fields

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def variant_search_page(request):
    """Generates the variant_search page, with initial variant_search json embedded."""

    initial_json = json.loads(
        variant_search_page_data(request).content
    )

    return render_with_initial_json('variant_search.html', initial_json)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def variant_search_page_data(request):
    """Returns a JSON object containing information needed to display the variant search page
    ::

      json_response = {
         'user': {..},
         'variants': [..],
       }
    Args:
        project_guid (string): GUID of the Project under case review.
    """

    if request.GET.get("f"):
        # single-family search mode
        family_guid = request.GET.get("f")
        family = Family.objects.get(guid=family_guid)

        # TODO handle family-not-found

        project = family.project

        # check permissions
        if not request.user.has_perm(CAN_VIEW, project) and not request.user.is_staff:
            raise PermissionDenied

        project_guids = [project.guid]
        family_guids = [family_guid]
    else:
        # all-families-in-a-project search mode
        family_guids = None
        if request.GET.get("p"):
            project_guid = request.GET.get("p")
            project = Project.objects.get(guid=project_guid)
            # TODO handle project-not-found

            # check permissions
            if not request.user.has_perm(CAN_VIEW, project) and not request.user.is_staff:
                raise PermissionDenied

            project_guids = [project.guid]
        else:
            # all projects search mode permissions to access
            project_guids = [p.guid for p in Project.objects.filter(can_view_group__user=request.user)]


    # get all datasets
    dataset_info = _retrieve_datasets(
        project_guids=project_guids,
        family_guids=family_guids,
        individual_guids=None,
        sample_types=None,
        analysis_types=None,
        only_loaded_datasets=True
    )

    # retrieve search params from hash or use default values
    search_params_hash = request.GET.get("h")
    if search_params_hash is not None:
        search_params = {}  # TODO retrieve search params for hash
        raise ValueError("Not implemented")

    else:
        search_params = {
            'dataset_guids': [],
            'project_guids': project_guids,
            'family_guids': [],
        }

    # TODO adjust search params that are no-longer valid

    json_response = {
        'user': _get_json_for_user(request.user),
        'project': _get_json_for_project(project, request.user),
        'variants': {},
    }

    return create_json_response(json_response)


_SAMPLE_TYPES = set([sample_type[0] for sample_type in Sample.SAMPLE_TYPE_CHOICES])
_ANALYSIS_TYPES = set([analysis_type[0] for analysis_type in Dataset.ANALYSIS_TYPE_CHOICES])


def _retrieve_datasets(
        cursor,
        project_guids,
        family_guids=None,
        individual_guids=None,
        sample_types=None,
        analysis_types=None,
        only_loaded_datasets=True,
):
    """Retrieves information on datasets that match all of the given critera.

    Args:
        cursor: connected database cursor that can be used to execute SQL queries.
        project_guids (list): List of projects
        family_guids (list): (optional) only consider datasets that have samples for individuals in these families.
        individual_guids (list): (optional) only consider datasets that have samples for these individuals
        sample_types (list): (optional) only consider datasets that have samples of these types (eg. "WES", "WGS", "RNA", etc.)
            See models.Sample.SAMPLE_TYPE_CHOICES for the full list of possible values.
        analysis_types (list): (optional) only consider datasets with this analysis type (eg. "SV", "VARIANT_CALLS", etc.)
            See models.Dataset.ANALYSIS_TYPE_CHOICES for the full list of possible values.
        only_loaded_datasets (bool): only return loaded datasets
    Returns:
        2-tuple with dictionaries: (families_by_guid, individuals_by_guid)
    """

    # make sure the user has permissions to access these projects
    # SQL injection

    WHERE_clause = "p.guid IN (" + ", ".join("%s"*len(project_guids)) + ")"
    WHERE_clause_args = list(project_guids)

    if family_guids is not None:
        WHERE_clause += " AND "
        WHERE_clause += "f.guid IN (" + ", ".join("%s"*len(family_guids)) + ")"
        WHERE_clause_args = list(family_guids)

    if individual_guids is not None:
        WHERE_clause += " AND "
        WHERE_clause += "i.guid IN (" + ", ".join("%s"*len(individual_guids)) + ")"
        WHERE_clause_args = list(individual_guids)

    if sample_types is not None:
        unexpected_sample_types = set(sample_types) - set(_SAMPLE_TYPES)
        if len(unexpected_sample_types) > 0:
            raise ValueError("Invalid sample_type(s): %s" % (unexpected_sample_types,))
        WHERE_clause += " AND "
        WHERE_clause += "s.sample_type IN (" + ", ".join("%s"*len(sample_types)) + ")"
        WHERE_clause_args = list(sample_types)

    if analysis_types is not None:
        unexpected_analysis_types = set(analysis_types) - set(_ANALYSIS_TYPES)
        if len(unexpected_analysis_types) > 0:
            raise ValueError("Invalid analysis_type(s): %s" % (unexpected_analysis_types,))
        WHERE_clause += " AND "
        WHERE_clause += "d.analysis_type IN (" + ", ".join("%s"*len(analysis_types)) + ")"
        WHERE_clause_args = list(analysis_types)

    if only_loaded_datasets:
        WHERE_clause += " AND d.is_loaded=TRUE "

    datasets_query = """
        SELECT DISTINCT
          p.guid AS project_guid,
          p.name AS project_name,
          f.guid AS family_guid,
          f.family_id AS family_id,
          i.guid AS individual_guid,
          i.individual_id AS individual_id,
          i.display_name AS individual_display_name,
          s.guid AS sample_guid,
          s.sample_type AS sample_type,
          s.sample_id AS sample_id,
          d.guid AS dataset_guid,
          d.dataset_id AS dataset_id,
          d.dataset_location AS dataset_location,
          d.analysis_type AS dataset_analysis_type,
          d.is_loaded AS dataset_is_loaded,
          d.loaded_date AS dataset_loaded_date
        FROM seqr_project AS p
          JOIN seqr_family AS f ON f.project_id=p.id
          JOIN seqr_individual AS i ON i.family_id=f.id
          JOIN seqr_sample AS s ON s.individual_id=i.id
          JOIN seqr_dataset_samples AS ds ON ds.sample_id=s.id
          JOIN seqr_dataset AS d ON d.id=ds.dataset_id
        WHERE %s
    """.strip() % WHERE_clause

    cursor.execute(datasets_query, WHERE_clause_args)

    columns = [col[0] for col in cursor.description]

    families_by_guid = {}
    individuals_by_guid = {}
    for row in cursor.fetchall():
        record = dict(zip(columns, row))

        family_guid = record['family_guid']
        if family_guid not in families_by_guid:
            families_by_guid[family_guid] = _get_json_for_family_fields(record)
            families_by_guid[family_guid]['individualGuids'] = set()

        individual_guid = record['individual_guid']
        if individual_guid not in individuals_by_guid:
            individuals_by_guid[individual_guid] = _get_json_for_individual_fields(record)
            phenotips_data = individuals_by_guid[individual_guid]['phenotipsData']
            if phenotips_data:
                try:
                    individuals_by_guid[individual_guid]['phenotipsData'] = json.loads(phenotips_data)
                except Exception as e:
                    logger.error("Couldn't parse phenotips: %s", e)
            individuals_by_guid[individual_guid]['sampleGuids'] = set()

            families_by_guid[family_guid]['individualGuids'].add(individual_guid)

    return families_by_guid, individuals_by_guid
