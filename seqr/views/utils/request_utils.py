from django.core.exceptions import PermissionDenied

from seqr.models import Project, CAN_VIEW


def _get_project_and_check_permissions(project_guid, user):
    """Retrieves Project with the given guid after checking that the given user has permission to
     retrieve the given project.

     Args:
         project_guid (string): GUID of project to retrieve
         user (User): Django User object
     """

    projects = Project.objects.filter(guid=project_guid)
    if not projects:
        raise ValueError("Invalid project GUID: %s" % project_guid)

    project = projects[0]

    if not user.is_staff and not user.has_perm(CAN_VIEW, project):
        raise PermissionDenied("%s does not have VIEW permissions for %s" % (user, project))

    return project
