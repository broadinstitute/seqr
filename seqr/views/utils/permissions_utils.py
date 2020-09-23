from django.core.exceptions import PermissionDenied
from django.db.models.query_utils import Q

from seqr.models import Project, CAN_VIEW, CAN_EDIT, IS_OWNER
from seqr.views.utils.terra_api_utils import service_account_session


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


def is_staff(user, session):
    return session['anvil'] and service_account_session.is_staff(user.anviluser.anvil_user_name)

def has_perm(user, permission_level, project, session):
    # the 'service_account_session' below will be replaced by 'session' after seqr client ID is whitelisted
    session = service_account_session
    is_staff_user = session.is_staff(user.anviluser.anvil_user_name)
    if is_staff_user and not project.disable_staff_access:
        return True
    collaborators = session.get_workspace_acl(project.workspace_namespace, project.workspace_name)
    if user.username in collaborators.keys():
        permission = collaborators[user.username]
        if permission['pending']:
            return False
        if permission_level is IS_OWNER:
            return permission['accessLevel'] == 'OWNER'
        if permission_level is CAN_EDIT:
            return (permission['accessLevel'] == 'WRITER') or (permission['accessLevel'] == 'OWNER')
        return True
    return False


def has_project_permissions(project, user, session=None, can_edit=False, is_owner=False):
    permission_level = CAN_VIEW
    if can_edit:
        permission_level = CAN_EDIT
    if is_owner:
        permission_level = IS_OWNER

    if session and session['anvil']:
        return has_perm(user, permission_level, project, session)
    else:
        return user.has_perm(permission_level, project) or (user.is_staff and not project.disable_staff_access)


def check_project_permissions(project, user, **kwargs):
    if has_project_permissions(project, user, **kwargs):
        return

    raise PermissionDenied("{user} does not have sufficient permissions for {project}".format(
        user=user, project=project))


def check_user_created_object_permissions(obj, user, session=None):
    if is_staff(user, session) or obj.created_by == user:
        return
    raise PermissionDenied("{user} does not have edit permissions for {object}".format(user=user, object=obj))


def check_multi_project_permissions(obj, user, session=None):
    for project in obj.projects.all():
        try:
            check_project_permissions(project, user, session=session)
            return
        except PermissionDenied:
            continue
    raise PermissionDenied("{user} does not have view permissions for {object}".format(user=user, object=obj))


def _get_anvil_projects_user_can_view(user, session):
    """
    . Fetch a workspace list with a false “public” attribute
    . If using a service account, filter out those user doesn’t have access
    . Get a corresponding project list of the workspaces
    . General project jsons
    """
    # the 'service_account_session' below will be replaced by 'session' after seqr client ID is whitelisted
    session = service_account_session
    is_staff_user = session.is_staff(user.anviluser.anvil_user_name)
    requested_fields = 'public,workspace.name,workspace.namespace,workspace.workspaceId'
    workspace_list = session.list_workspaces(requested_fields)
    workspaces = []
    for ws in workspace_list:
        if not ws['public']:
            if is_staff_user:
                workspaces.append(ws['workspace']['name'])
            else:
                try:
                    acl = session.get_workspace_acl(ws['workspace']['namespace'], ws['workspace']['name'])
                except Exception:
                    acl={}
                if user.anviluser.anvil_user_name in acl.keys():
                    workspaces.append(ws['workspace']['name'])
    if is_staff_user:
        return Project.objects.filter(name__in=workspaces, disable_staff_access=False)
    return Project.objects.filter(name__in=workspaces)


def get_projects_user_can_view(user, session=None):
    if session and session['anvil']:
        return _get_anvil_projects_user_can_view(user, session)
    can_view_filter = Q(can_view_group__user=user)
    if user.is_staff:
        return Project.objects.filter(can_view_filter | Q(disable_staff_access=False))
    else:
        return Project.objects.filter(can_view_filter)


def check_mme_permissions(submission, user, session=None):
    project = submission.individual.family.project
    check_project_permissions(project, user, session=session)
    if not project.is_mme_enabled:
        raise PermissionDenied('Matchmaker is not enabled')


