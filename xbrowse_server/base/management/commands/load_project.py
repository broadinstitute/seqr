from optparse import make_option
from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--force-annotations', action="store_true", dest='force_annotations', default=False),
    )

    def handle(self, *args, **options):
        force_annotations = options.get('force_annotations')
        for project_id in args:
            xbrowse_controls.load_project(project_id, force_annotations=force_annotations)
