import logging

from django.core.management.base import BaseCommand

from panelapp.panelapp_utils import import_all_panels, PANEL_APP_SOURCES

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('source', help='Panel App Source', choices=PANEL_APP_SOURCES.keys())

    def handle(self, *args, **options):
        source = options['source']
        logger.info(f'Starting import of all gene lists from Panel App {source}')
        import_all_panels(source)

        logger.info('---Done---')
