import logging

from django.core.management.base import BaseCommand

from panelapp.panelapp_utils import import_all_panels

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('panel_app_url', help='Panel App API URL')

    def handle(self, *args, **options):
        panel_app_url = options['panel_app_url']
        logger.info('Starting import of all gene lists from Panel App [{}]'.format(panel_app_url))
        import_all_panels(None, panel_app_url)

        logger.info('---Done---')
