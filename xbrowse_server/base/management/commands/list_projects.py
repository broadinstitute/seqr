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

            print(("%3d families: %s\n"
                   "%3d individuals\n"
                   "project id:   %s\n"
                   "VCF files: %s\n"
                   "Reference Populations: \n%s \n") % (
                    len({i.get_family_id() for i in individuals} - {None,}),
                    ", ".join([family.family_id for family in project.family_set.all()]),
                    len(individuals),
                    project.project_id,
                    ", ".join([v.path() for v in project.get_all_vcf_files()]) + "\n",
                    "\n".join([p.slug + " name: " + p.name for p in project.private_reference_populations.all()])
                    #project.families_by_vcf().items()
            ))
