from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q

from seqr.models import Project, VariantTagType

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--source', help='Project to copy tags from', required=True)
        parser.add_argument('--target', help='Project to copy tags to', required=True)

    def handle(self, *args, **options):

        source_project_name = options['source']
        target_project_name = options['target']

        source_project = Project.objects.get(Q(name=source_project_name) | Q(guid=source_project_name))

        target_project = Project.objects.get(Q(name=target_project_name) | Q(guid=target_project_name))

        tags = VariantTagType.objects.filter(project=source_project)

        for tag in tags:
            tag.pk = None
            tag.id = None
            tag.project = target_project
            tag.save()
            logger.info('Saved tag %s (new id = %d)' % (tag.name, tag.id))
