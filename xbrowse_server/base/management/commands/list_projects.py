from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def handle(self, *args, **options):
        if args:
            projects = [Project.objects.get(project_id=arg) for arg in args]
        else:
            projects = Project.objects.all()

        for project in projects:
            individuals = project.get_individuals()

            print("%3d families: %s,  %3d individuals,  project id:   %s.  VCF files: %s \n %s" % (
                len({i.get_family_id() for i in individuals} - {None,}),
                project.family_set.all(),
                len(individuals),
                project.project_id,
                project.get_all_vcf_files(),
                project.families_by_vcf().items()
            ))
