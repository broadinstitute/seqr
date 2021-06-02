import logging

from django.contrib.auth.decorators import user_passes_test, login_required
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Concat
from django.db.models import Value

from seqr.models import Project, ProjectCategory, CAN_VIEW, CAN_EDIT
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.views.utils.terra_api_utils import is_anvil_authenticated, user_get_workspace_acl, list_anvil_workspaces,\
    anvil_enabled, user_get_workspace_access_level, WRITER_ACCESS_LEVEL, OWNER_ACCESS_LEVEL,\
    PROJECT_OWNER_ACCESS_LEVEL, CAN_SHARE_PERM
from settings import API_LOGIN_REQUIRED_URL, ANALYST_USER_GROUP, PM_USER_GROUP, ANALYST_PROJECT_CATEGORY, \
    TERRA_WORKSPACE_CACHE_EXPIRE_SECONDS, SEQR_PRIVACY_VERSION, SEQR_TOS_VERSION, API_POLICY_REQUIRED_URL

logger = logging.getLogger(__name__)

def user_is_analyst(user):
    return bool(ANALYST_USER_GROUP) and user.groups.filter(name=ANALYST_USER_GROUP).exists()

def user_is_data_manager(user):
    return user.is_staff

def user_is_pm(user):
    return user.groups.filter(name=PM_USER_GROUP).exists() if PM_USER_GROUP else user.is_superuser

def _has_current_policies(user):
    if not hasattr(user, 'userpolicy'):
        return False

    current_privacy = user.userpolicy.privacy_version
    current_tos = user.userpolicy.tos_version
    return current_privacy == SEQR_PRIVACY_VERSION and current_tos == SEQR_TOS_VERSION


# User access decorators
def _require_permission(user_permission_test_func, error='User has insufficient permission'):
    def test_user(user):
        if not user_permission_test_func(user):
            raise PermissionDenied(error)
        return True
    return test_user

_active_required = user_passes_test(_require_permission(lambda user: user.is_active, error='User is no longer active'))
_current_policies_required = user_passes_test(_has_current_policies, login_url=API_POLICY_REQUIRED_URL)

def login_active_required(wrapped_func=None, login_url=API_LOGIN_REQUIRED_URL):
    def decorator(view_func):
        return login_required(_active_required(view_func), login_url=login_url)
    if wrapped_func:
        return decorator(wrapped_func)
    return decorator

def login_and_policies_required(view_func):
    return login_active_required(_current_policies_required(view_func))

def _user_has_policies_and_passes_test(user_permission_test_func):
    def decorator(view_func):
        return login_and_policies_required(user_passes_test(_require_permission(user_permission_test_func))(view_func))
    return decorator

analyst_required = _user_has_policies_and_passes_test(user_is_analyst)
data_manager_required = _user_has_policies_and_passes_test(user_is_data_manager)
pm_required = _user_has_policies_and_passes_test(user_is_pm)
pm_or_data_manager_required = _user_has_policies_and_passes_test(
    lambda user: user_is_data_manager(user) or user_is_pm(user))
superuser_required = _user_has_policies_and_passes_test(lambda user: user.is_superuser)


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
    if access_level in [WRITER_ACCESS_LEVEL, OWNER_ACCESS_LEVEL, PROJECT_OWNER_ACCESS_LEVEL]:
        return CAN_EDIT
    return CAN_VIEW if access_level == 'READER' else None


def anvil_has_perm(user, permission_level, project):
    if not project_has_anvil(project):
        return False
    return has_workspace_perm(user, permission_level, project.workspace_namespace, project.workspace_name)


def has_workspace_perm(user, permission_level, namespace, name, can_share=False, meta_fields=None):
    kwargs = {'meta_fields': meta_fields } if meta_fields else {}
    workspace_permission = user_get_workspace_access_level(user, namespace, name, **kwargs)
    if not workspace_permission:
        return False
    if can_share and not workspace_permission.get(CAN_SHARE_PERM):
        return False
    permission = _map_anvil_seqr_permission(workspace_permission)
    if permission != CAN_EDIT and permission != permission_level:
        return False
    return workspace_permission if meta_fields else True


def check_workspace_perm(user, permission_level, namespace, name, can_share=False, meta_fields=None):
    workspace_meta = has_workspace_perm(user, permission_level, namespace, name, can_share, meta_fields)
    if workspace_meta:
        return workspace_meta

    message = "User does not have sufficient permissions for workspace {namespace}/{name}".format(
        namespace=namespace, name=name)
    logger.warning(message)
    raise PermissionDenied(message)


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


def get_project_guids_user_can_view(user):
    cache_key = 'projects__{}'.format(user)
    project_guids = safe_redis_get_json(cache_key)
    if project_guids is not None:
        return project_guids

    is_data_manager = user_is_data_manager(user)
    if is_data_manager:
        projects = Project.objects.all()
    else:
        projects = get_local_access_projects(user)

    project_guids = [p.guid for p in projects.only('guid')]
    if is_anvil_authenticated(user) and not is_data_manager:
        workspaces = ['/'.join([ws['workspace']['namespace'], ws['workspace']['name']]) for ws in
                      list_anvil_workspaces(user)]
        project_guids += [p.guid for p in Project.objects.filter(workspace_name__isnull=False).exclude(
            workspace_name='').exclude(guid__in=project_guids).annotate(
            workspace=Concat('workspace_namespace', Value('/'), 'workspace_name')).filter(
            workspace__in=workspaces).only('guid')]

    safe_redis_set_json(cache_key, project_guids, expire=TERRA_WORKSPACE_CACHE_EXPIRE_SECONDS)

    return project_guids


def get_local_access_projects(user):
    projects = Project.objects.filter(can_view_group__user=user)
    if user_is_analyst(user):
        projects = (projects | _get_analyst_projects())
    return projects


def check_mme_permissions(submission, user):
    project = submission.individual.family.project
    check_project_permissions(project, user)
    if not project.is_mme_enabled:
        raise PermissionDenied('Matchmaker is not enabled')

def has_case_review_permissions(project, user):
    if not project.has_case_review:
        return False
    return has_project_permissions(project, user, can_edit=True)
