from django.core.exceptions import PermissionDenied
from django.db.models.query_utils import Q

from seqr.models import Project, CAN_VIEW, CAN_EDIT, IS_OWNER


def _validate_permissions_arg(permission_level):
    if permission_level not in (CAN_VIEW, CAN_EDIT, IS_OWNER):
        raise ValueError("Unexpected permission level: %(permission_level)s" % locals())


def get_project_and_check_permissions(project_guid, user, permission_level=CAN_VIEW):
    """Retrieves Project with the given guid after checking that the given user has permission to
     retrieve the given project.

     Args:
         project_guid (string): GUID of project to retrieve
         user (User): Django User object
         permission_level (string): One of the constants: CAN_VIEW, CAN_EDIT, IS_OWNER
     """
    _validate_permissions_arg(permission_level)

    projects = Project.objects.filter(guid=project_guid)
    if not projects:
        raise ValueError("Invalid project GUID: %s" % project_guid)

    project = projects[0]
    check_permissions(project, user, permission_level)

    return project


def check_permissions(project, user, permission_level=CAN_VIEW):
    if user.has_perm(permission_level, project) or (user.is_staff and not project.disable_staff_access):
        pass
    else:
        raise PermissionDenied("%(user)s does not have %(permission_level)s permissions for %(project)s" % locals())


def get_projects_user_can_view(user):
    can_view_filter = Q(can_view_group__user=user)
    if user.is_staff:
        return Project.objects.filter(can_view_filter | Q(disable_staff_access=False))
    else:
        return Project.objects.filter(can_view_filter)


def get_projects_user_can_edit(user):
    can_edit_filter = Q(can_edit_group__user=user)
    if user.is_staff:
        return Project.objects.filter(can_edit_filter | Q(disable_staff_access=False))
    else:
        return Project.objects.filter(can_edit_filter)


def add_user_to_project(user, project, permission_level=CAN_VIEW):
    _validate_permissions_arg(permission_level)

    if user.is_staff:
        return

    if permission_level == CAN_VIEW:
        project.can_view_group.user_set.add(user)
    elif permission_level == CAN_EDIT:
        project.can_edit_group.user_set.add(user)


