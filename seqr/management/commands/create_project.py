import logging

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db.models.query_utils import Q

from seqr.views.apis.project_api import create_project

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create a new project.'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--description', help="Project description", default="")
        parser.add_argument('-c', '--collaborator', help="Username or email of collaborator(s)", action="append")
        parser.add_argument('-m', '--manager', help="Username or email of manager(s)", action="append")
        parser.add_argument('project_name', help="Project name")

    def handle(self, *args, **options):

        project = create_project(
            name=options.get('project_name'),
            description=options.get('description'))

        logger.info("Created project %s" % project.guid)
        for label, users, user_set in (
            ("collaborator", options.get("collaborator", []), project.can_view_group.user_set),
            ("manager", options.get("manager", []), project.can_edit_group.user_set),
        ):
            print(label, users)
            for user in users:
                try:
                    user = User.objects.get(Q(username=user) | Q(email=user))
                    user_set.add(user)
                    logger.info("Added %s %s to project %s" % (label, user, project))
                except ObjectDoesNotExist:
                    raise CommandError("User not found: %s" % user)

