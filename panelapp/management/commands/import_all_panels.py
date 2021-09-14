import logging

from django.core.management.base import BaseCommand

from panelapp.panelapp_utils import import_all_panels
from settings import PANEL_APP_API_URL

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info('Starting import of all gene lists from Panel App [{}]'.format(PANEL_APP_API_URL))
        import_all_panels(None)

        logger.info('---Done---')
