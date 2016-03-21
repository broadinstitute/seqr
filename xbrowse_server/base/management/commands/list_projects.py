from django.core.management.base import BaseCommand
from optparse import make_option


from xbrowse_server.base.models import Project

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('-s', '--simple', action="store_true", help="List only the project ids"),


    def handle(self, *args, **options):
        if args:
            projects = [Project.objects.get(project_id=arg) for arg in args]
        else:
            projects = Project.objects.all()

        #f = open("all_xbrowse_individuals.txt", "w")
        #f.write("\t".join(["project_id", "family_id", "individual_id"]) + "\n")
        #for project in projects:
        #    individuals = project.get_individuals()
        #    for i in individuals:
        #        f.write("\t".join([project.project_id, i.family.family_id, i.indiv_id]) + "\n")
        #f.close()

        if options.get('simple'):
            for project in projects:
                print(project.project_id)
            return

        for project in projects:
            print("=============")
            print((
               "project id:   %s\n"
               "%3d families: %s\n"
               "%3d individuals: %s\n"
               "%3d collaborators: %s\n"
               "VCF files:\n%s"
               "reference populations: %s \n"
               ) % (
                project.project_id,
                len({i.get_family_id() for i in project.get_individuals()} - {None,}),
                ", ".join([family.family_id for family in project.family_set.all()]),
                len(project.get_individuals()),
                ", ".join([i.indiv_id for i in project.get_individuals()]),
                len(project.get_collaborators()),
                [u.email for u in project.get_collaborators()],
                "\n".join([v.path() for v in project.get_all_vcf_files()]) + "\n",
                ",".join([p.slug + " name: " + p.name for p in project.private_reference_populations.all()])
                #project.families_by_vcf().items()
                ))
