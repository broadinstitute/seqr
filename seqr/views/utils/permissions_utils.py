from django.core.exceptions import PermissionDenied
from django.db.models.query_utils import Q

from seqr.models import Project, CAN_VIEW, CAN_EDIT, IS_OWNER
from seqr.views.utils.terra_api_utils import service_account_session, anvilSessionStore


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


def has_project_permissions(project, user, can_edit=False, is_owner=False):
    permission_level = CAN_VIEW
    if can_edit:
        permission_level = CAN_EDIT
    if is_owner:
        permission_level = IS_OWNER

    return user.has_perm(permission_level, project) or (user.is_staff and not project.disable_staff_access)


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
    # the 'service_account_session' below will be replaced by 'session' after seqr client ID is whitelisted
    is_staff_user = user.is_staff
    session = service_account_session
    requested_fields = 'public,workspace.name,workspace.namespace,workspace.workspaceId'
    workspace_list = session.list_workspaces(requested_fields)
    workspaces = []
    for ws in workspace_list:
        if not ws['public']:
            if is_staff_user:
                workspaces.append('/'.join([ws['workspace']['namespace'], ws['workspace']['name']]))
            else:
                acl = session.get_workspace_acl(ws['workspace']['namespace'], ws['workspace']['name'])
                if user.email in acl.keys():
                    workspaces.append('/'.join([ws['workspace']['namespace'], ws['workspace']['name']]))
    return workspaces


def get_projects_user_can_view(user):
    if anvilSessionStore.get_session(user):
        workspaces = _get_workspaces_user_can_view(user)
        can_view_filter = (Q(can_view_group__user=user) & Q(workspace__isnull=True)) | Q(workspace__in=workspaces)
    else:
        can_view_filter = Q(can_view_group__user=user)
    if user.is_staff:
        return Project.objects.filter(can_view_filter | Q(disable_staff_access=False))
    else:
        return Project.objects.filter(can_view_filter).distinct()


def check_mme_permissions(submission, user):
    project = submission.individual.family.project
    check_project_permissions(project, user)
    if not project.is_mme_enabled:
        raise PermissionDenied('Matchmaker is not enabled')
