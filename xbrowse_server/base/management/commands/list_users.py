from django.core.management.base import BaseCommand

from xbrowse_server.base.models import User

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def handle(self, *args, **options):
        if args:
            users = [User.objects.get(username=arg) for arg in args]
        else:
            users = User.objects.all()

        print("Superusers: ")
        for user in [u for u in users if u.is_superuser]:
            print("username: %s     email: %s      name: %s %s" % (user.username, user.email, user.first_name, user.last_name))

        print("\nStaff: ")
        for user in [u for u in users if u.is_staff]:
            print("username: %s     email: %s      name: %s %s" % (user.username, user.email, user.first_name, user.last_name))
