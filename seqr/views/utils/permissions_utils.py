from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Concat
from django.db.models import Value, TextField
from guardian.shortcuts import get_objects_for_user

from seqr.models import Project, CAN_VIEW, CAN_EDIT
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.redis_utils import safe_redis_get_json, safe_redis_set_json
from seqr.views.utils.terra_api_utils import is_anvil_authenticated, user_get_workspace_acl, list_anvil_workspaces,\
    anvil_enabled, user_get_workspace_access_level, get_anvil_group_members, user_get_anvil_groups, \
    WRITER_ACCESS_LEVEL, OWNER_ACCESS_LEVEL, PROJECT_OWNER_ACCESS_LEVEL, CAN_SHARE_PERM
from settings import API_LOGIN_REQUIRED_URL, ANALYST_USER_GROUP, PM_USER_GROUP, INTERNAL_NAMESPACES, \
    TERRA_WORKSPACE_CACHE_EXPIRE_SECONDS, SEQR_PRIVACY_VERSION, SEQR_TOS_VERSION, API_POLICY_REQUIRED_URL
from typing import Callable, Optional

logger = SeqrLogger(__name__)


def get_anvil_analyst_user_emails(user):
    return get_anvil_group_members(user, ANALYST_USER_GROUP, use_sa_credentials=True)


def get_analyst_user_emails(user):
    if not ANALYST_USER_GROUP:
        return []
    if anvil_enabled():
        return get_anvil_analyst_user_emails(user)
    return set(User.objects.filter(groups__name=ANALYST_USER_GROUP).values_list('email', flat=True))


def get_pm_user_emails(user):
    if not PM_USER_GROUP:
        return []
    if anvil_enabled():
        return get_anvil_group_members(user, PM_USER_GROUP)
    return list(User.objects.filter(groups__name=PM_USER_GROUP).values_list('email', flat=True))


def user_is_analyst(user):
    if anvil_enabled():
        return ANALYST_USER_GROUP in user_get_anvil_groups(user)
    return bool(ANALYST_USER_GROUP) and user.groups.filter(name=ANALYST_USER_GROUP).exists()


def user_is_data_manager(user):
    return user.is_staff


def user_is_pm(user):
    if anvil_enabled():
        return PM_USER_GROUP in user_get_anvil_groups(user)
    return user.groups.filter(name=PM_USER_GROUP).exists() if PM_USER_GROUP else user.is_superuser


def _has_current_policies(user):
    if not hasattr(user, 'userpolicy'):
        return False

    current_privacy = user.userpolicy.privacy_version
    current_tos = user.userpolicy.tos_version
    return current_privacy == SEQR_PRIVACY_VERSION and current_tos == SEQR_TOS_VERSION


# User access decorators
def _require_permission(user_permission_test_func: Callable, error: str = 'User has insufficient permission') -> Callable:
    def test_user(user):
        if not user_permission_test_func(user):
            raise PermissionDenied(error)
        return True
    return test_user

_active_required = user_passes_test(_require_permission(lambda user: user.is_active, error='User is no longer active'))
def _current_policies_required(view_func: Callable, policy_url: str = API_POLICY_REQUIRED_URL) -> Callable:
    return user_passes_test(_has_current_policies, login_url=policy_url)(view_func)

def login_active_required(wrapped_func: Optional[Callable] = None, login_url: str = API_LOGIN_REQUIRED_URL) -> Callable:
    def decorator(view_func):
        return login_required(_active_required(view_func), login_url=login_url)
    if wrapped_func:
        return decorator(wrapped_func)
    return decorator

def login_and_policies_required(view_func: Callable, login_url: str = API_LOGIN_REQUIRED_URL, policy_url: str = API_POLICY_REQUIRED_URL) -> Callable:
    return login_active_required(_current_policies_required(view_func, policy_url=policy_url), login_url=login_url)

def active_user_has_policies_and_passes_test(user_permission_test_func: Callable) -> Callable:
    def decorator(view_func):
        return login_and_policies_required(user_passes_test(_require_permission(user_permission_test_func))(view_func))
    return decorator


analyst_required = active_user_has_policies_and_passes_test(user_is_analyst)
data_manager_required = active_user_has_policies_and_passes_test(user_is_data_manager)
pm_required = active_user_has_policies_and_passes_test(user_is_pm)
pm_or_data_manager_required = active_user_has_policies_and_passes_test(
    lambda user: user_is_data_manager(user) or user_is_pm(user))
superuser_required = active_user_has_policies_and_passes_test(lambda user: user.is_superuser)


def is_internal_anvil_project(project):
    return anvil_enabled() and project.workspace_namespace in INTERNAL_NAMESPACES


def get_internal_projects():
    if anvil_enabled():
        return Project.objects.filter(workspace_namespace__in=INTERNAL_NAMESPACES)
    return Project.objects.all()


def get_project_and_check_permissions(project_guid, user, **kwargs):
    """Retrieves Project with the given guid after checking that the given user has permission to
     retrieve the given project.

     Args:
         project_guid (string): GUID of project to retrieve
         user (User): Django User object
         can_edit (bool): If user need edit permission
     """
    return _get_project_and_check_permissions(project_guid, user, check_project_permissions, **kwargs)

def get_project_and_check_pm_permissions(project_guid, user, override_permission_func=None):
    return _get_project_and_check_permissions(project_guid, user, _check_project_pm_permission,
                                              override_permission_func=override_permission_func)

def _get_project_and_check_permissions(project_guid, user, _check_permission_func, **kwargs):
    project = Project.objects.get(guid=project_guid)
    _check_permission_func(project, user, **kwargs)
    return project

def _check_project_pm_permission(project, user, override_permission_func=None, **kwargs):
    if user_is_pm(user) or (project.has_case_review and has_project_permissions(project, user, can_edit=True)):
        return

    if override_permission_func and override_permission_func(project, user):
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
    logger.warning(message, user)
    raise PermissionDenied(message)


def get_workspace_collaborator_perms(user, workspace_namespace, workspace_name):
    workspace_acl = user_get_workspace_acl(user, workspace_namespace, workspace_name)
    permission_levels = {}
    for email in workspace_acl.keys():
        permission_level = _map_anvil_seqr_permission(workspace_acl[email])
        if permission_level:
            permission_levels.update({email.lower(): permission_level})
    return permission_levels


def has_project_permissions(project, user, can_edit=False):
    permission_level = CAN_VIEW
    if can_edit:
        permission_level = CAN_EDIT

    return user_is_data_manager(user) or \
           (not can_edit and project.all_user_demo and project.is_demo) or \
           _user_project_permission(user, permission_level, project)


def _user_project_permission(user, permission_level, project):
    if anvil_enabled():
        return anvil_has_perm(user, permission_level, project)
    return user.has_perm(permission_level, project)


def check_project_permissions(project, user, **kwargs):
    if has_project_permissions(project, user, **kwargs):
        return

    raise PermissionDenied("{user} does not have sufficient permissions for {project}".format(
        user=user, project=project))


def _is_user_created_object(obj, user):
    return obj.created_by == user


def check_user_created_object_permissions(obj, user):
    if _is_user_created_object(obj, user):
        return
    raise PermissionDenied("{user} does not have edit permissions for {object}".format(user=user, object=obj))


def _get_all_can_view_project_guids_set(user):
    return set(get_project_guids_user_can_view(user, limit_data_manager=False))


def check_projects_view_permission(projects, user):
    no_access_projects = set(projects.values_list('guid', flat=True)) - _get_all_can_view_project_guids_set(user)
    if no_access_projects:
        raise PermissionDenied(f"{user} does not have sufficient permissions for {','.join(no_access_projects)}")


def check_locus_list_permissions(locus_list, user):
    if locus_list.is_public or _is_user_created_object(locus_list, user):
        return
    access_projects = set(locus_list.projects.values_list('guid', flat=True)).intersection(
        _get_all_can_view_project_guids_set(user)
    )
    if not access_projects:
        raise PermissionDenied(f'{user} does not have view permissions for {locus_list}')


def get_project_guids_user_can_view(user, limit_data_manager=True):
    if user_is_data_manager(user) and not limit_data_manager:
        return list(Project.objects.values_list('guid', flat=True))

    cache_key = 'projects__{}'.format(user)
    project_guids = safe_redis_get_json(cache_key)
    if project_guids is not None:
        return project_guids

    if is_anvil_authenticated(user):
        workspaces = ['/'.join([ws['workspace']['namespace'], ws['workspace']['name']]) for ws in
                      list_anvil_workspaces(user)]
        projects = Project.objects.annotate(
            workspace=Concat('workspace_namespace', Value('/', output_field=TextField()), 'workspace_name')
        ).filter(workspace__in=workspaces)
    else:
        projects = get_objects_for_user(user, CAN_VIEW, Project)

    projects = projects | Project.objects.filter(all_user_demo=True, is_demo=True)

    project_guids = [p.guid for p in projects.distinct().only('guid')]

    safe_redis_set_json(cache_key, sorted(project_guids), expire=TERRA_WORKSPACE_CACHE_EXPIRE_SECONDS)

    return project_guids


def check_mme_permissions(submission, user):
    project = submission.individual.family.project
    check_project_permissions(project, user)
    if not (project.is_mme_enabled and not project.is_demo):
        raise PermissionDenied('Matchmaker is not enabled')

def has_case_review_permissions(project, user):
    if not project.has_case_review:
        return False
    return has_project_permissions(project, user, can_edit=True)
