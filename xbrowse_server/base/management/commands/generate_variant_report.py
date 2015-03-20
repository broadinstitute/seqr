from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ProjectTag, VariantTag


class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def handle(self, *args, **options):
        if not args:
            print("Please provide the project_id as a command line arg")
            return

        project_id = Project.objects.get(project_id=args[0])
        #project = Project.objects.get(project_id=args[0])

        # get variants that have been tagged
        for variant_tag in VariantTag.objects.filter(project_tag__project=project_id):  #, project_tag__tag="report"):
            print(variant_tag.xpos, variant_tag.ref, variant_tag.alt)
            #to_project_tag = ProjectTag.objects.get(project=to_project, tag=from_tag.project_tag.tag)
