import logging
from django.core.management.base import BaseCommand
from seqr.management.commands.check_for_new_samples_from_pipeline import update_project_saved_variant_genotypes
from seqr.models import Project, Family, Sample, Dataset

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reload cached genotypes for saved variants'

    def add_arguments(self, parser):
        parser.add_argument('project')
        parser.add_argument('--family-guid', help='optional family to reload variants for')

    def handle(self, *args, **options):
        project =  Project.objects.get(guid=options['project'])
        family_guid = options['family_guid']
        family_guids = [family_guid] if family_guid else Family.objects.filter(project=project).values_list('guid', flat=True)

        samples = Sample.objects.filter(individual__family__project_id=project.id, is_active=True)
        if family_guid:
            samples = samples.filter(individual__family__guid=family_guid)
        dataset_types = {
            f'{dataset_type}_{sample_type}' if dataset_type == Dataset.DATASET_TYPE_SV_CALLS else dataset_type
            for dataset_type, sample_type in samples.values_list('dataset_type', 'sample_type').distinct()
        }
        for dataset_type in sorted(dataset_types):
            update_project_saved_variant_genotypes(project, family_guids, dataset_type)

        logger.info('Done')
