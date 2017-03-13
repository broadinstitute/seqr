from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create a new project.'

    def add_arguments(self, parser):
        parser.add_argument('-u', '--username', help="Username", required=True)
        parser.add_argument('-e', '--email-address', help="Email address")
        parser.add_argument('-p', '--password', help="Password")

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email_address', None)
        password = options.get('password', None)

        try:
            user = User.objects.get(username=username)
        except:
            raise CommandError("Username %s not found." % username)


        if email:
            user.email = email
        if password:
            user.password = password
        user.save()
        print("Updated " + username)


