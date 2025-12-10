import logging

from django.core.management.base import BaseCommand

from panelapp.panelapp_utils import import_all_panels, delete_all_panels, PANEL_APP_SOURCES

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('source', help='Panel App Source', choices=PANEL_APP_SOURCES.keys())
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete all panels/gene lists with URL prefixed with given <panel_app_url>',
        )

    def handle(self, *args, **options):
        source = options['source']
        if options['delete']:
            logger.info(f'Starting delete of all {source} gene lists')
            delete_all_panels(source)
        else:
            logger.info(f'Starting import of all gene lists from Panel App {source}')
            import_all_panels(source)

        logger.info('---Done---')
