from django.core.management.base import BaseCommand
from optparse import make_option
import tasks


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--no-async', action="store_true", dest='no_async'),
        make_option('--no-annotate', action="store_true", dest='no_annotate', default=False),
    )

    def handle(self, *args, **options):

        no_async = options.get('no_async')
        annotate = not options.get('no_annotate')

        for project_id in args:
            #if no_async:
            if True:  # removing async option for now
                tasks.reload_project(project_id, annotate=annotate)
            else: 
                tasks.reload_project.delay(project_id, annotate=annotate)
