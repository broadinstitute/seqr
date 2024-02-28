from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand, CommandError
import json
import logging

from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Family, Sample
from seqr.utils.file_utils import file_iter, does_file_exist
from seqr.utils.search.add_data_utils import notify_search_data_loaded
from seqr.views.utils.dataset_utils import match_and_update_search_samples
from seqr.views.utils.variant_utils import reset_cached_search_results, update_projects_saved_variant_json

logger = logging.getLogger(__name__)

GS_PATH_TEMPLATE = 'gs://seqr-hail-search-data/v03/{path}/runs/{version}/'
DATASET_TYPE_MAP = {'GCNV': Sample.DATASET_TYPE_SV_CALLS}


class Command(BaseCommand):
    help = 'Check for newly loaded seqr samples'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('version')
        parser.add_argument('--allow-failed', action='store_true')

    def handle(self, *args, **options):
        path = options['path']
        version = options['version']
        genome_version, dataset_type = path.split('/')
        dataset_type = DATASET_TYPE_MAP.get(dataset_type, dataset_type)

        if Sample.objects.filter(data_source=version, is_active=True).exists():
            logger.info(f'Data already loaded for {path}: {version}')
            return

        logger.info(f'Loading new samples from {path}: {version}')
        gs_path = GS_PATH_TEMPLATE.format(path=path, version=version)
        if not does_file_exist(gs_path + '_SUCCESS'):
            if options['allow_failed']:
                logger.warning(f'Loading for failed run {path}: {version}')
            else:
                raise CommandError(f'Run failed for {path}: {version}, unable to load data')

        metadata = json.loads(next(line for line in file_iter(gs_path + 'metadata.json')))
        families = Family.objects.filter(guid__in=metadata['family_samples'].keys())
        if len(families) < len(metadata['family_samples']):
            invalid = metadata['family_samples'].keys() - set(families.values_list('guid', flat=True))
            raise CommandError(f'Invalid families in run metadata {path}: {version} - {", ".join(invalid)}')

        family_project_map = {f.guid: f.project for f in families.select_related('project')}
        samples_by_project = defaultdict(list)
        for family_guid, sample_ids in metadata['family_samples'].items():
            samples_by_project[family_project_map[family_guid]] += sample_ids

        sample_project_tuples = []
        invalid_genome_version_projects = []
        for project, sample_ids in samples_by_project.items():
            sample_project_tuples += [(sample_id, project.name) for sample_id in sample_ids]
            project_genome_version = GENOME_VERSION_LOOKUP.get(project.genome_version, project.genome_version)
            if project_genome_version != genome_version:
                invalid_genome_version_projects.append((project.guid, project_genome_version))

        if invalid_genome_version_projects:
            raise CommandError(
                f'Data has genome version {genome_version} but the following projects have conflicting versions: ' +
                ', '.join([f'{project} ({invalid_version})' for project, invalid_version in invalid_genome_version_projects])
            )

        sample_type = metadata['sample_type']
        logger.info(f'Loading {len(sample_project_tuples)} {sample_type} {dataset_type} samples in {len(samples_by_project)} projects')
        updated_samples, inactivated_sample_guids, *args = match_and_update_search_samples(
            projects=samples_by_project.keys(),
            sample_project_tuples=sample_project_tuples,
            sample_data={'data_source': version, 'elasticsearch_index': ';'.join(metadata['callsets'])},
            sample_type=sample_type,
            dataset_type=dataset_type,
            user=None,
        )

        # Reset cached results for all projects, as seqr AFs will have changed for all projects when new data is added
        reset_cached_search_results(project=None)

        # Send loading notifications
        for project, sample_ids in samples_by_project.items():
            project_updated_samples = updated_samples.filter(individual__family__project=project)
            notify_search_data_loaded(
                project, dataset_type, sample_type, inactivated_sample_guids,
                updated_samples=project_updated_samples, num_samples=len(sample_ids),
            )

        # Reload saved variant JSON
        updated_annotation_samples = Sample.objects.filter(is_active=True, dataset_type=dataset_type)
        if dataset_type == Sample.DATASET_TYPE_SV_CALLS:
            updated_annotation_samples = updated_annotation_samples.filter(sample_type=sample_type)
        projects = Family.objects.filter(
            project__genome_version=genome_version.replace('GRCh', ''), individual__sample__in=updated_annotation_samples,
        ).order_by('id').values('project').annotate(family_ids=ArrayAgg('family_id', distinct=True)).values_list(
            'project__id', 'project__name', 'family_ids',
        )
        import pdb; pdb.set_trace()
        update_projects_saved_variant_json(projects, user_email='manage_command', dataset_type=dataset_type)

        logger.info('DONE')
