from optparse import make_option
from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+')
        parser.add_argument('--force-annotations', action="store_true", dest='force_annotations', default=False)
        parser.add_argument('--force-clean', action="store_true", dest='force_clean', default=False)
        parser.add_argument('--all', action="store_true", dest='load_all', default=False)


    def handle(self, *args, **options):
        force_annotations = options.get('force_annotations')
        force_clean = options.get('force_clean')
        load_all = options.get('load_all')
        if load_all:
            project_ids = [p.project_id for p in Project.objects.all().order_by('-last_accessed_date')]
        else:
            project_ids = args
        for project_id in project_ids:
            if force_clean:
                xbrowse_controls.clean_project(project_id)
            xbrowse_controls.load_project(project_id, force_annotations=force_annotations)
