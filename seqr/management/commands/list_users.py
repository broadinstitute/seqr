import logging

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db.models import Q

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Print a list of users. If no options are specified, all users will be printed.'

    def add_arguments(self, parser):
        parser.add_argument('-r', '--regular-users', action="store_true", help="Print out regular users")
        parser.add_argument('-s', '--staff', action="store_true", help="Print out staff users")
        parser.add_argument('-u', '--superusers', action="store_true", help="Print out superusers")

    def handle(self, *args, **options):
        print_regular_users = options.get('regular_users', False)
        print_staff = options.get('staff', False)
        print_superusers = options.get('superusers', False)
        print_all = not print_regular_users and not print_staff and not print_superusers

        if print_all or print_regular_users:
            self.print_users("regular user(s)", User.objects.filter(~Q(is_staff=True) & ~Q(is_superuser=True)))
        if print_all or print_staff:
            self.print_users("staff", User.objects.filter(is_staff=True))
        if print_all or print_superusers:
            self.print_users("superuser(s)", User.objects.filter(is_superuser=True))

    def print_users(self, label, users):
        """Utility method that prints out a set of users.

        Args:
            label: A short description of the users in the list.
            users: A list of django User objects.
        """
        logger.info("-- %d %s --" % (len(users), label))
        for user in users:
            print("  %15s   %40s      %s %s" % (user.username, user.email, user.first_name, user.last_name))
