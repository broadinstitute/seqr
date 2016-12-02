from django.utils.text import slugify
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from xbrowse_server.base.models import Project

class Command(BaseCommand):
    help = 'Create a new project.'

    def add_arguments(self, parser):
        parser.add_argument('-u', '--username', help="Username", required=True)

    def handle(self, *args, **options):
        username = options.get('username')

        usernames = User.objects.filter(username=username)
        if len(usernames) == 0:
            raise CommandError("Username %s not found." % username)
        elif len(usernames) >= 2:
            raise CommandError("Username %s is duplicated." % username)

        user = usernames[0]
        user.delete()
        print("Deleted " + username + "!")


