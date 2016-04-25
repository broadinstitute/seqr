import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Individual, Project

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def handle(self, *args, **options):
        if args:
            individuals = Individual.objects.filter(project__project_id=args[0])
        else:
            individuals = Individual.objects.all()
        #if args:
        #    individuals = [User.objects.get(username=arg) for arg in args]
        
        for indiv in individuals:
            print("\t".join(["project:%s", "family:%s", "indiv:%s", "affected:%s", "sex:%s"]) % (indiv.project.project_id, indiv.family.family_id, indiv.indiv_id, "yes" if indiv.affected else "no", indiv.gender))
#            print("%15s   %40s      %10s %10s %s" % (user.username, user.email, user.first_name, user.last_name, [p.project_id for p in Project.objects.all().order_by('project_id') if p.can_view(user)]))
