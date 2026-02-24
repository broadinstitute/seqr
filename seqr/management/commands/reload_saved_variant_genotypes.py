import logging
from django.core.management.base import BaseCommand
from seqr.management.commands.check_for_new_samples_from_pipeline import update_project_saved_variant_genotypes
from seqr.models import Project, Family, Sample
from seqr.utils.search.utils import clickhouse_only

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reload cached genotypes for saved variants'

    def add_arguments(self, parser):
        parser.add_argument('project')
        parser.add_argument('--family-guid', help='optional family to reload variants for')

    @clickhouse_only
    def handle(self, *args, **options):
        project =  Project.objects.get(guid=options['project'])
        family_guid = options['family_guid']
        family_guids = [family_guid] if family_guid else Family.objects.filter(project=project).values_list('guid', flat=True)

        samples = Sample.objects.filter(individual__family__project_id=project.id, is_active=True)
        if family_guid:
            samples = samples.filter(individual__family__guid=family_guid)
        dataset_types = {
            f'{dataset_type}_{sample_type}' if dataset_type == Sample.DATASET_TYPE_SV_CALLS else dataset_type: dataset_type
            for dataset_type, sample_type in samples.values_list('dataset_type', 'sample_type').distinct()
        }
        for clickhouse_dataset_type, dataset_type in dataset_types.items():
            update_project_saved_variant_genotypes(
                project.id, project.genome_version, family_guids, project.guid,
                samples=samples.filter(dataset_type=dataset_type), clickhouse_dataset_type=clickhouse_dataset_type,
            )

        logger.info('Done')
