"""
APIs used by the main seqr dashboard page
"""

import logging

from django.db import models

from seqr.models import ProjectCategory, Sample, Family, Project
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_projects
from seqr.views.utils.permissions_utils import get_project_guids_user_can_view, login_and_policies_required
from settings import ANALYST_PROJECT_CATEGORY

logger = logging.getLogger(__name__)


@login_and_policies_required
def dashboard_page_data(request):
    """Returns a JSON object containing information used by the dashboard page:
    ::

      json_response = {
         'user': {..},
         'familiesByGuid': {..},
         'individualsByGuid': {..},
       }
    """
    projects_by_guid = _get_projects_json(request.user)
    project_categories_by_guid = _retrieve_project_categories_by_guid(projects_by_guid.keys())

    json_response = {
        'projectsByGuid': projects_by_guid,
        'projectCategoriesByGuid': project_categories_by_guid,
    }

    return create_json_response(json_response)


def _get_projects_json(user):
    project_guids = get_project_guids_user_can_view(user)
    if not project_guids:
        return {}

    projects = Project.objects.filter(guid__in=project_guids)
    projects_with_counts = projects.annotate(
        models.Count('family', distinct=True), models.Count('family__individual', distinct=True),
        models.Count('family__savedvariant', distinct=True))

    projects_by_guid = {p['projectGuid']: p for p in get_json_for_projects(projects, user=user)}
    for project in projects_with_counts:
        projects_by_guid[project.guid]['numFamilies'] = project.family__count
        projects_by_guid[project.guid]['numIndividuals'] = project.family__individual__count
        projects_by_guid[project.guid]['numVariantTags'] = project.family__savedvariant__count

    analysis_status_counts = Family.objects.filter(project__in=projects).values(
        'project__guid', 'analysis_status').annotate(count=models.Count('*'))
    for agg in analysis_status_counts:
        project_guid = agg['project__guid']
        if 'analysisStatusCounts' not in projects_by_guid[project_guid]:
            projects_by_guid[project_guid]['analysisStatusCounts'] = {}
        projects_by_guid[project_guid]['analysisStatusCounts'][agg['analysis_status']] = agg['count']

    sample_type_status_counts = Sample.objects.filter(individual__family__project__in=projects, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS
    ).values(
        'individual__family__project__guid', 'sample_type',
    ).annotate(count=models.Count('individual_id', distinct=True))
    for agg in sample_type_status_counts:
        project_guid = agg['individual__family__project__guid']
        if 'sampleTypeCounts' not in projects_by_guid[project_guid]:
            projects_by_guid[project_guid]['sampleTypeCounts'] = {}
        projects_by_guid[project_guid]['sampleTypeCounts'][agg['sample_type']] = agg['count']

    return projects_by_guid


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
    project_categories = ProjectCategory.objects.filter(
        projects__guid__in=project_guids).exclude(name=ANALYST_PROJECT_CATEGORY).distinct()

    project_categories_by_guid = {}
    for project_category in project_categories:
        project_categories_by_guid[project_category.guid] = project_category.json()

    return project_categories_by_guid
