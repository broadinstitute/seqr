from django.core.management.base import BaseCommand
from optparse import make_option
from django.contrib.auth.models import User


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--password'),
        make_option('--username'),
    )

    def handle(self, *args, **options):
        email = args[0]
        username = options.get('username')
        if not username:
            username = User.objects.make_random_password()
        password = options.get('password')
        user = User.objects.create_user(username, email, password)
        profile = user.profile