from optparse import make_option
from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project

import signal, traceback
def quit_handler(signum,frame):
    traceback.print_stack()
signal.signal(signal.SIGQUIT,quit_handler)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('--force-load-annotations', action="store_true", dest='force_load_annotations', default=False)
        parser.add_argument('--force-load-variants', action="store_true", dest='force_load_variants', default=False)
        parser.add_argument('--force-clean', action="store_true", dest='force_clean', default=False)
        parser.add_argument('--all', action="store_true", dest='load_all', default=False)
        parser.add_argument('-s', '--start-from-chrom', help="Start from this chromosome (eg. '1', '2', 'X', etc.)")
        parser.add_argument('-e', '--end-with-chrom', help="End after this chromosome is loaded (eg. '1', '2', 'X', etc.)")


    def handle(self, *args, **options):
        force_load_annotations = options.get('force_load_annotations')
        force_load_variants = options.get('force_load_variants')
        force_clean = options.get('force_clean')
        load_all = options.get('load_all')
        if load_all:
            project_ids = [p.project_id for p in Project.objects.all().order_by('-last_accessed_date')]
        else:
            project_ids = args

        mark_as_loaded = True if not options.get("end_with_chrom") else False
        for project_id in project_ids:
            if force_clean:
                xbrowse_controls.clean_project(project_id)
            xbrowse_controls.load_project(project_id, force_load_annotations=force_load_annotations, force_load_variants=force_load_variants,
                                          mark_as_loaded = mark_as_loaded, start_from_chrom=options.get("start_from_chrom"), end_with_chrom=options.get("end_with_chrom"))
