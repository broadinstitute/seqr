from optparse import make_option
from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--force-annotations', action="store_true", dest='force_annotations', default=False),
        make_option('--all', action="load_all", dest='load_all', default=False),
    )

    def handle(self, *args, **options):
        force_annotations = options.get('force_annotations')
        load_all = options.get('load_all')
        if load_all:
            for project in Project.objects.all().order_by('-last_accessed_date'):
                xbrowse_controls.load_project(project.project_id, force_annotations=force_annotations)
        for project_id in args:
            xbrowse_controls.load_project(project_id, force_annotations=force_annotations)
