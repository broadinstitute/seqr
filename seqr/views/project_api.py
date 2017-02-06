import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Project, ProjectCategory, CAN_EDIT
from seqr.views.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils import create_json_response, _get_json_for_project


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_project_info(request, project_guid):
    """Modify Project fields.

    Args:
        project_guid (string): GUID of the project.
    """

    project = Project.objects.get(guid=project_guid)

    # check permissions
    if not request.user.has_perm(CAN_EDIT, project) and not request.user.is_staff:
        raise PermissionDenied

    request_json = json.loads(request.body)
    form_data = request_json['form']

    if 'name' in form_data:
        project.name = form_data.get('name')
        project.save()
    elif 'description' in form_data:
        project.description = form_data.get('description')
        project.save()

    return create_json_response({project.guid: _get_json_for_project(project, request.user.is_staff)})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_project_categories(request, project_guid):
    project = Project.objects.get(guid=project_guid)

    # check permissions
    if not request.user.has_perm(CAN_EDIT, project) and not request.user.is_staff:
        raise PermissionDenied

    request_json = json.loads(request.body)
    form_data = request_json['form']

    current_categories = set(form_data['categories'])

    categories_to_create = set(current_categories)

    project_categories_by_guid = {}
    for project_category in ProjectCategory.objects.all():
        if project_category.guid in current_categories:
            project_category.projects.add(project)
            categories_to_create.remove(project_category.guid)
            # TODO update color
        else:
            project_category.projects.remove(project)
            if project_category.projects.count() == 0:
                project_category.delete()

        project_categories_by_guid[project_category.guid] = project_category.json()

    # create new categories
    for category_name in categories_to_create:
        project_category = ProjectCategory.objects.create(name=category_name, created_by=request.user)
        project_category.projects.add(project)

        project_categories_by_guid[project_category.guid] = project_category.json()

    projects_by_guid = {
        project.guid: _get_json_for_project(project, request.user.is_staff)
    }

    return create_json_response({
        'projectsByGuid': projects_by_guid,
        'projectCategoriesByGuid': project_categories_by_guid,
    })
