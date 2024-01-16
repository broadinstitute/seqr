from django.core.management.base import BaseCommand, CommandError

from seqr.models import Project, Sample

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('project')

    def handle(self, *args, **options):
        project = Project.objects.get(guid=options['project'])

        if input(f'Are you sure you want to deactivate search for {project.name} (y/n)? ') != 'y':
            raise CommandError('Error: user did not confirm')

        updated = Sample.bulk_update(user=None, update_json={'is_active': False}, individual__family__project=project)

        logger.info(f'Deactivated {len(updated)} samples')
