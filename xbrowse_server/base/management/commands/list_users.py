import os
from django.core.management.base import BaseCommand

from xbrowse_server.base.models import User, Project

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        if args:
            users = [User.objects.get(username=arg) for arg in args]
        else:
            users = User.objects.all()

        print("Superusers: ")
        for user in [u for u in users if u.is_superuser]:
            print("%15s   %40s      %s %s" % (user.username, user.email, user.first_name, user.last_name))

        print("\nStaff: ")
        for user in [u for u in users if u.is_staff]:
            print("%15s   %40s      %s %s" % (user.username, user.email, user.first_name, user.last_name))


        print("\nAll non-superusers, non-staff: " ) 
        all_other_users = sorted([u for u in users if not u.is_staff and not u.is_superuser], key=lambda u: u.email)

        import collections
        emails = collections.defaultdict(int)  # used for finding duplicates
        
        user_emails_filename = "xbrowse_user_emails.tsv"
        f = open(user_emails_filename, "w")
        print("\nWriting all user emails to %s" % os.path.abspath(user_emails_filename))
        for user in all_other_users:
            emails[user.email] += 1
            print("%15s   %40s      %10s %10s %s" % (user.username, user.email, user.first_name, user.last_name, [p.project_id for p in Project.objects.all().order_by('project_id') if p.can_view(user)]))
            f.write("%s\n" % user.email)
        f.close()

        print("\nWrote all user emails to %s" % os.path.abspath(user_emails_filename))
        print("\nDuplicate accounts with same email address:")
        found = False
        for email, counter in emails.items():
            if counter > 1:
                print("%s  - count: %s" % (email, counter))
                found = True
        if not found:
            print("    None found")
