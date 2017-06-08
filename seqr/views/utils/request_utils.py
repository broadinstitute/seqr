from django.core.exceptions import PermissionDenied

from seqr.models import Project, CAN_VIEW, CAN_EDIT, IS_OWNER


def _get_project_and_check_permissions(project_guid, user, permission_level=CAN_VIEW):
    """Retrieves Project with the given guid after checking that the given user has permission to
     retrieve the given project.

     Args:
         project_guid (string): GUID of project to retrieve
         user (User): Django User object
         permission_level (string): One of the constants: CAN_VIEW, CAN_EDIT, IS_OWNER
     """
    if permission_level not in (CAN_VIEW, CAN_EDIT, IS_OWNER):
        raise ValueError("Unexpected permission level: %(permission_level)s" % locals())

    projects = Project.objects.filter(guid=project_guid)
    if not projects:
        raise ValueError("Invalid project GUID: %s" % project_guid)

    project = projects[0]

    if not user.is_staff and not user.has_perm(permission_level, project):
        raise PermissionDenied("%(user)s does not have %(permission_level)s permissions for %(project)s" % locals())

    return project
