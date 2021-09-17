import logging

from django.core.management.base import BaseCommand

from panelapp.panelapp_utils import import_all_panels, delete_all_panels

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('panel_app_url', help='Panel App API URL')
        parser.add_argument('--label', help='Optional label to add to the list description')
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete all panels/gene lists with URL prefixed with given <panel_app_url>',
        )

    def handle(self, *args, **options):
        panel_app_url = options['panel_app_url']
        if options['delete']:
            logger.info('Starting delete of all gene lists with URL prefixed with [{}]'.format(panel_app_url))
            delete_all_panels(None, panel_app_url)
        else:
            logger.info('Starting import of all gene lists from Panel App [{}]'.format(panel_app_url))
            import_all_panels(None, panel_app_url, label=options['label'])

        logger.info('---Done---')
