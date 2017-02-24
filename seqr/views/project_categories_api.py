"""APIs for setting Project categories"""


import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Project, ProjectCategory, CAN_EDIT
from seqr.views.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.json_utils import create_json_response, _get_json_for_project


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_project_categories(request, project_guid):
    """Update ProjectCategories for the given project.

    Args:
        project_guid (string): GUID of the project that should be updated

    HTTP POST
        Request body - should contain one or more json params:
            categories: a list of category GUIDs for the categories assigned to the given project

        Response body - will be json with the following structure, representing the updated project,
            as well all categories in seqr:
            {
                'projectsByGuid':  {
                    <projectGuid1> : { ... <project key-value pairs> ... }
                }
                'projectCategoriesByGuid':  {
                    <projectCategoryGuid1> : { ... <category key-value pairs> ... }
                    <projectCategoryGuid2> : { ... <category key-value pairs> ... }
                }
            }
    """
    project = Project.objects.get(guid=project_guid)

    # check permissions
    if not request.user.has_perm(CAN_EDIT, project) and not request.user.is_staff:
        raise PermissionDenied

    request_json = json.loads(request.body)

    if 'form' not in request_json:
        return create_json_response({}, status=400, reason="Invalid request: 'form' not in request_json")

    form_data = request_json['form']

    # categories currently assigned to this project
    current_categories = set(form_data['categories'])

    # remove ProjectCategory mappings for categories the user wants to remove from this project
    project_categories_already_assigned = set()
    for project_category in project.projectcategory_set.all():
        if project_category.guid not in current_categories:
            project_category.projects.remove(project)
            if project_category.projects.count() == 0:
                project_category.delete()
        else:
            # also record the project_category guids for which there's already a ProjectCategory
            # object mapped to this project and doesn't need to be added or removed
            project_categories_already_assigned.add(project_category.guid)


    # add mappings for ProjectCategory objects that are mapped to other projects, and that the user now wants to add to this project also
    project_categories_to_create = set(current_categories)
    for project_category in ProjectCategory.objects.filter(guid__in=current_categories):
        if project_category.guid not in project_categories_already_assigned:
            project_category.projects.add(project)

        project_categories_to_create.remove(project_category.guid)

    # create ProjectCategory objects for new categories, and add mappings for them to this project
    project_categories_by_guid = {}
    for category_name in project_categories_to_create:
        project_category = ProjectCategory.objects.create(name=category_name, created_by=request.user)
        project_category.projects.add(project)

        project_categories_by_guid[project_category.guid] = project_category.json()

    projects_by_guid = {
        project.guid: _get_json_for_project(project, request.user)
    }

    return create_json_response({
        'projectsByGuid': projects_by_guid,
        'projectCategoriesByGuid': project_categories_by_guid,
    })
