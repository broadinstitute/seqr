from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

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

        for project in projects:
            print("=============")
            print((
               "project id:   %s\n\n"
               "%3d families: %s\n\n"
               "%3d individuals: %s\n\n"
               "VCF files:\n%s\n"
               "reference populations: %s \n"
               ) % (
                project.project_id,
                len({i.get_family_id() for i in project.get_individuals()} - {None,}),
                ", ".join([family.family_id for family in project.family_set.all()]),
                len(project.get_individuals()),
                ", ".join([i.indiv_id for i in project.get_individuals()]),
                "\n".join([v.path() for v in project.get_all_vcf_files()]) + "\n",
                ",".join([p.slug + " name: " + p.name for p in project.private_reference_populations.all()])
                #project.families_by_vcf().items()
                ))
