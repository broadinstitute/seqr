from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        if args:
            projects = [Project.objects.get(project_id=arg) for arg in args]
        else:
            projects = Project.objects.all()

        for project in projects:
            print((               
                    "%s,\t"
                    "users: %s,\t"
                    "%3d families,\t"
                    "%3d individuals,\t"
                    "VCF files: %s,\n") % (
                project.project_id,
                ", ".join([(u[0].email or u[0].username) for u in project.get_users()]),
                len({i.get_family_id() for i in project.get_individuals()} - {None,}),
                len(project.get_individuals()),
                ", ".join([v.path() for v in project.get_all_vcf_files()]) + "\n",
                #project.families_by_vcf().items()
                ))
