from django.core.management.base import BaseCommand, CommandError

from seqr.models import Project, SavedVariant, VariantTag, VariantNote, VariantFunctionalData

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('project_prefix')

    def handle(self, *args, **options):
        projects = Project.objects.filter(name__startswith=options['project_prefix'], projectcategory__name='Demo')
        if input('Are you sure you want to clear the tags for the following {} projects (y/n): {}\n'.format(
                projects.count(), ', '.join([p.name for p in projects]))) != 'y':
            raise CommandError('User aborted')

        total_deleted, all_deletion_counts = VariantTag.bulk_delete(user=None, saved_variants__family__project__in=projects)

        deleted, deletion_counts = VariantNote.bulk_delete(user=None, saved_variants__family__project__in=projects)
        total_deleted += deleted
        all_deletion_counts.update(deletion_counts)

        deleted, deletion_counts = VariantFunctionalData.bulk_delete(user=None, saved_variants__family__project__in=projects)
        total_deleted += deleted
        all_deletion_counts.update(deletion_counts)

        deleted, deletion_counts = SavedVariant.bulk_delete(user=None, family__project__in=projects)
        total_deleted += deleted
        all_deletion_counts.update(deletion_counts)

        logger.info('Deleted {} entities:'.format(total_deleted))
        for model, count in all_deletion_counts.items():
            logger.info('    {}: {}'.format(model.lstrip('seqr.'), count))
