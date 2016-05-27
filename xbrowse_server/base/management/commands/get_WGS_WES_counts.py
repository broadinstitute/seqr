from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual


class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    #   parser.add_argument('-s', '--simple', action="store_true", help="List only the project ids"),


    def handle(self, *args, **options):
        def get_count(project_id):
            return len(Individual.objects.filter(project_id=project_id))
        if args:
            projects = [Project.objects.get(project_id=arg) for arg in args]
        else:
            projects = Project.objects.all()

        wgs_counts=0
        rna_counts=0
        wes_counts=0
        for project in projects:
            project_name = project.project_name.lower()
            if "deprecated" not in project_name:
                if "wgs" in project_name or "genome" in project_name:
                    samples_in_this_project=get_count(project.id)
                    wgs_counts += samples_in_this_project

                elif "rna" in project_name:
                    rna_counts+=get_count(project.id)
                else:
                    wes_counts+=get_count(project.id)


        print("%s WGS samples \n%s RNA samples \n%s WES samples" % (wgs_counts, rna_counts, wes_counts))
