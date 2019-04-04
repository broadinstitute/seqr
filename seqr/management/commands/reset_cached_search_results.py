import logging
from django.core.management.base import BaseCommand
from seqr.models import Project
from seqr.views.utils.variant_utils import reset_cached_search_results

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reset all saved variant search results'

    def add_arguments(self, parser):
        parser.add_argument('--project', help='optional project to reload variants for')

    def handle(self, *args, **options):
        """transfer project"""
        project_name = options['project']
        project = Project.objects.get(name=project_name) if project_name else None
        reset_cached_search_results(project=project)
        logger.info('Reset cached search results for {}'.format(project_name or 'all projects'))


