from django.core.exceptions import PermissionDenied
from django.db.models.query_utils import Q
from django.db.models.functions import Concat
from django.db.models import Value

from seqr.models import Project, CAN_VIEW, CAN_EDIT, IS_OWNER
from seqr.views.utils.terra_api_utils import is_google_authenticated, user_get_workspace_acl, list_anvil_workspaces,\
    anvil_enabled, user_get_workspace_access_level


def get_project_and_check_permissions(project_guid, user, **kwargs):
    """Retrieves Project with the given guid after checking that the given user has permission to
     retrieve the given project.

     Args:
         project_guid (string): GUID of project to retrieve
         user (User): Django User object
         can_edit (bool): If user need edit permission
         is_owner (bool): If user need owner permission
     """
    project = Project.objects.get(guid=project_guid)
    check_project_permissions(project, user, **kwargs)
    return project


def project_has_anvil(project):
    return anvil_enabled() and bool(project.workspace_namespace and project.workspace_name)


def _map_anvil_seqr_permission(anvil_permission):
    if anvil_permission.get('pending'):
        return None
    if anvil_permission['accessLevel'] in ['WRITER', 'OWNER', 'PROJECT_OWNER']:
        return CAN_EDIT
    return CAN_VIEW if anvil_permission['accessLevel'] == 'READER' else None


def anvil_has_perm(user, permission_level, project):
    if not project_has_anvil(project):
        return False
    workspace_permission = user_get_workspace_access_level(user, project.workspace_namespace, project.workspace_name)
    if not workspace_permission:
        return False
    permission = _map_anvil_seqr_permission(workspace_permission)
    return True if permission == CAN_EDIT else permission == permission_level


def get_collaborator_permission_levels(user, workspace_namespace, workspace_name):
    workspace_acl = user_get_workspace_acl(user, workspace_namespace, workspace_name)
    permission_levels = {}
    for email in workspace_acl.keys():
        permission_level = _map_anvil_seqr_permission(workspace_acl[email])
        if permission_level:
            permission_levels.update({email: permission_level})
    return permission_levels


def has_project_permissions(project, user, can_edit=False, is_owner=False):
    permission_level = CAN_VIEW
    if can_edit:
        permission_level = CAN_EDIT
    if is_owner:
        permission_level = IS_OWNER

    return user.has_perm(permission_level, project) or (user.is_staff and not project.disable_staff_access)\
        or anvil_has_perm(user, permission_level, project)


def check_project_permissions(project, user, **kwargs):
    if has_project_permissions(project, user, **kwargs):
        return

    raise PermissionDenied("{user} does not have sufficient permissions for {project}".format(
        user=user, project=project))


def check_user_created_object_permissions(obj, user):
    if user.is_staff or obj.created_by == user:
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


def _get_workspaces_user_can_view(user):
    workspace_list = list_anvil_workspaces(user, fields='public,accessLevel,workspace.name,workspace.namespace,workspace.workspaceId')
    return ['/'.join([ws['workspace']['namespace'], ws['workspace']['name']]) for ws in workspace_list if not ws.get('public', True)]


def get_projects_user_can_view(user):
    can_view_filter = Q(can_view_group__user=user)
    if user.is_staff:
        can_view_filter = can_view_filter | Q(disable_staff_access=False)

    if is_google_authenticated(user):
        workspaces = _get_workspaces_user_can_view(user)
        anvil_permitted_projects = Project.objects.annotate(
            workspace = Concat('workspace_namespace', Value('/'), 'workspace_name')).filter(workspace__in=workspaces)
        return (anvil_permitted_projects | Project.objects.filter(can_view_filter)).distinct()
    else:
        return Project.objects.filter(can_view_filter)


def check_mme_permissions(submission, user):
    project = submission.individual.family.project
    check_project_permissions(project, user)
    if not project.is_mme_enabled:
        raise PermissionDenied('Matchmaker is not enabled')
