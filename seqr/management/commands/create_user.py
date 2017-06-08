from django.utils.text import slugify
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from xbrowse_server.base.models import Project, UserProfile

class Command(BaseCommand):
    help = 'Create a new project.'

    def add_arguments(self, parser):
        parser.add_argument('-u', '--username', help="Username", required=True)
        parser.add_argument('-e', '--email-address', help="Email address", required=True)
        parser.add_argument('-p', '--password', help="Password", required=True)

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email_address', None)
        password = options.get('password', None)

        try:
            User.objects.get(username=username)
        except:
            pass
        else:
            raise CommandError("Username %s already exists." % username)

        if not username:
            raise CommandError("Username is empty.")

        user = User.objects.create(username=username)
        if email:
            user.email = email
        if password:
            user.password = password
        user.save()

        UserProfile.objects.create(user=user, display_name=username)
        print("Created " + username + "!")

