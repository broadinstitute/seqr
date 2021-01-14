from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Concat
from django.db.models import Value

from seqr.models import Project, ProjectCategory, CAN_VIEW, CAN_EDIT
from seqr.views.utils.terra_api_utils import is_google_authenticated, user_get_workspace_acl, list_anvil_workspaces,\
    anvil_enabled, user_get_workspace_access_level
from settings import API_LOGIN_REQUIRED_URL, ANALYST_USER_GROUP, PM_USER_GROUP, ANALYST_PROJECT_CATEGORY

def user_is_analyst(user):
    return bool(ANALYST_USER_GROUP) and user.groups.filter(name=ANALYST_USER_GROUP).exists()

def user_is_data_manager(user):
    return user.is_staff

def user_is_pm(user):
    return user.groups.filter(name=PM_USER_GROUP).exists() if PM_USER_GROUP else user.is_superuser

# User access decorators
analyst_required = user_passes_test(user_is_analyst, login_url=API_LOGIN_REQUIRED_URL)
data_manager_required = user_passes_test(user_is_data_manager, login_url=API_LOGIN_REQUIRED_URL)
pm_required = user_passes_test(user_is_pm, login_url=API_LOGIN_REQUIRED_URL)

def _has_analyst_access(project):
    return project.projectcategory_set.filter(name=ANALYST_PROJECT_CATEGORY).exists()

def get_project_and_check_permissions(project_guid, user, **kwargs):
    """Retrieves Project with the given guid after checking that the given user has permission to
     retrieve the given project.

     Args:
         project_guid (string): GUID of project to retrieve
         user (User): Django User object
         can_edit (bool): If user need edit permission
     """
    return _get_project_and_check_permissions(project_guid, user, check_project_permissions, **kwargs)

def get_project_and_check_pm_permissions(project_guid, user):
    return _get_project_and_check_permissions(project_guid, user, _check_project_pm_permission)

def _get_project_and_check_permissions(project_guid, user, _check_permission_func, **kwargs):
    project = Project.objects.get(guid=project_guid)
    _check_permission_func(project, user, **kwargs)
    return project

def _check_project_pm_permission(project, user, **kwargs):
    if user_is_pm(user) or (project.has_case_review and has_project_permissions(project, user, can_edit=True)):
        return

    raise PermissionDenied("{user} does not have sufficient project management permissions for {project}".format(
        user=user, project=project))

def project_has_anvil(project):
    return anvil_enabled() and bool(project.workspace_namespace and project.workspace_name)


def _map_anvil_seqr_permission(anvil_permission):
    if anvil_permission.get('pending'):
        return None
    access_level = anvil_permission.get('accessLevel')
    if access_level in ['WRITER', 'OWNER', 'PROJECT_OWNER']:
        return CAN_EDIT
    return CAN_VIEW if access_level == 'READER' else None


def anvil_has_perm(user, permission_level, project):
    if not project_has_anvil(project):
        return False
    workspace_permission = user_get_workspace_access_level(user, project.workspace_namespace, project.workspace_name)
    if not workspace_permission:
        return False
    permission = _map_anvil_seqr_permission(workspace_permission)
    return True if permission == CAN_EDIT else permission == permission_level


def get_workspace_collaborator_perms(user, workspace_namespace, workspace_name):
    workspace_acl = user_get_workspace_acl(user, workspace_namespace, workspace_name)
    permission_levels = {}
    for email in workspace_acl.keys():
        permission_level = _map_anvil_seqr_permission(workspace_acl[email])
        if permission_level:
            permission_levels.update({email: permission_level})
    return permission_levels


def has_project_permissions(project, user, can_edit=False):
    permission_level = CAN_VIEW
    if can_edit:
        permission_level = CAN_EDIT

    return user_is_data_manager(user) or \
           (user_is_analyst(user) and _has_analyst_access(project)) or \
           user.has_perm(permission_level, project) or \
           anvil_has_perm(user, permission_level, project)


def check_project_permissions(project, user, **kwargs):
    if has_project_permissions(project, user, **kwargs):
        return

    raise PermissionDenied("{user} does not have sufficient permissions for {project}".format(
        user=user, project=project))


def check_user_created_object_permissions(obj, user):
    if obj.created_by == user:
        return
    raise PermissionDenied("{user} does not have edit permissions for {object}".format(user=user, object=obj))


def check_multi_project_permissions(obj, user):
    for project in obj.projects.all():
        try:
            check_project_permissions(project, user)
            return
        except PermissionDenied:
            continue
    raise PermissionDenied("{user} does not have view permissions for {object}".format(user=user, object=obj))


def _get_analyst_projects():
    return ProjectCategory.objects.get(name=ANALYST_PROJECT_CATEGORY).projects.all()


def get_projects_user_can_view(user):
    if user_is_data_manager(user):
        return Project.objects.all()

    projects = Project.objects.filter(can_view_group__user=user)
    if user_is_analyst(user):
        projects = (projects | _get_analyst_projects())

    if is_google_authenticated(user):
        workspaces = ['/'.join([ws['workspace']['namespace'], ws['workspace']['name']]) for ws in list_anvil_workspaces(user)]
        anvil_permitted_projects = Project.objects.annotate(
            workspace = Concat('workspace_namespace', Value('/'), 'workspace_name')).filter(workspace__in=workspaces)
        return (anvil_permitted_projects | projects).distinct()
    else:
        return projects.distinct()


def check_mme_permissions(submission, user):
    project = submission.individual.family.project
    check_project_permissions(project, user)
    if not project.is_mme_enabled:
        raise PermissionDenied('Matchmaker is not enabled')

def has_case_review_permissions(project, user):
    if not project.has_case_review:
        return False
    return has_project_permissions(project, user, can_edit=True)
