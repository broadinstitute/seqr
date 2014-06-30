from optparse import make_option

from django.core.management.base import BaseCommand

import tasks


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--force-annotations', action="store_true", dest='force_annotations', default=False),
    )

    def handle(self, *args, **options):
        force_annotations = options.get('force_annotations')
        for project_id in args:
            tasks.reload_project(project_id, force_annotations=force_annotations)
