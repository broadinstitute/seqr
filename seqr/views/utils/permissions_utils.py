from django.core.exceptions import PermissionDenied

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
    if not user.is_staff and not user.has_perm(permission_level, project):
        raise PermissionDenied("%(user)s does not have %(permission_level)s permissions for %(project)s" % locals())


def get_projects_user_can_view(user):
    if user.is_staff:
        return Project.objects.all()
    else:
        return Project.objects.filter(can_view_group__user=user)


def get_projects_user_can_edit(user):
    if user.is_staff:
        return Project.objects.all()
    else:
        return Project.objects.filter(can_edit_group__user=user)


def add_user_to_project(user, project, permission_level=CAN_VIEW):
    _validate_permissions_arg(permission_level)

    if user.is_staff:
        return

    if permission_level == CAN_VIEW:
        project.can_view_group.user_set.add(user)
    elif permission_level == CAN_EDIT:
        project.can_edit_group.user_set.add(user)


