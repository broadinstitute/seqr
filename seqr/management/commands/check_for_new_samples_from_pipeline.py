from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.db.models.functions import JSONObject
import json
import logging

from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Family, Sample, SavedVariant
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.file_utils import file_iter, does_file_exist
from seqr.utils.search.add_data_utils import notify_search_data_loaded
from seqr.utils.search.utils import parse_valid_variant_id
from seqr.utils.search.hail_search_utils import hail_variant_multi_lookup, search_data_type
from seqr.views.utils.dataset_utils import match_and_update_search_samples
from seqr.views.utils.variant_utils import reset_cached_search_results, update_projects_saved_variant_json, \
    get_saved_variants
from settings import SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = logging.getLogger(__name__)

GS_PATH_TEMPLATE = 'gs://seqr-hail-search-data/v03/{path}/runs/{version}/'
DATASET_TYPE_MAP = {'GCNV': Sample.DATASET_TYPE_SV_CALLS}
USER_EMAIL = 'manage_command'
MAX_LOOKUP_VARIANTS = 5000


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
        update_sample_data_by_project = {
            s['individual__family__project']: s for s in updated_samples.values('individual__family__project').annotate(
                samples=ArrayAgg(JSONObject(sample_id='sample_id', individual_id='individual_id')),
                family_guids=ArrayAgg('individual__family__guid', distinct=True),
            )
        }
        updated_project_families = []
        updated_families = set()
        for project, sample_ids in samples_by_project.items():
            project_sample_data = update_sample_data_by_project[project.id]
            notify_search_data_loaded(
                project, dataset_type, sample_type, inactivated_sample_guids,
                updated_samples=project_sample_data['samples'], num_samples=len(sample_ids),
            )
            project_families = project_sample_data['family_guids']
            updated_families.update(project_families)
            updated_project_families.append((project.id, project.name, project.genome_version, project_families))

        # Send failure notifications
        failed_family_samples = metadata.get('failed_family_samples', {})
        failed_families_by_guid = {f['guid']: f for f in Family.objects.filter(
            guid__in={family for families in failed_family_samples.values() for family in families}
        ).values('guid', 'family_id', 'project__name')}
        for check, check_failures in failed_family_samples.items():
            failures_by_project = defaultdict(list)
            for family_guid, failure_data in check_failures.items():
                family = failed_families_by_guid[family_guid]
                failures_by_project[family['project__name']].append(
                    f'- {family["family_id"]}: {"; ".join(failure_data["reasons"])}'
                )
            for project, failures in failures_by_project.items():
                summary = '\n'.join(sorted(failures))
                safe_post_to_slack(
                    SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL,
                    f'The following {len(failures)} families failed {check.replace("_", " ")} in {project}:\n{summary}'
                )

        # Reload saved variant JSON
        updated_variants_by_id = update_projects_saved_variant_json(
            updated_project_families, user_email=USER_EMAIL, dataset_type=dataset_type)

        self._reload_shared_variant_annotations(
            search_data_type(dataset_type, sample_type), genome_version, updated_variants_by_id, exclude_families=updated_families)

        logger.info('DONE')

    @staticmethod
    def _reload_shared_variant_annotations(data_type, genome_version, updated_variants_by_id=None, exclude_families=None):
        dataset_type = data_type.split('_')[0]
        is_sv = dataset_type.startswith(Sample.DATASET_TYPE_SV_CALLS)
        dataset_type = data_type.split('_')[0] if is_sv else data_type
        db_genome_version = genome_version.replace('GRCh', '')
        updated_annotation_samples = Sample.objects.filter(
            is_active=True, dataset_type=dataset_type,
            individual__family__project__genome_version=db_genome_version,
        )
        if exclude_families:
            updated_annotation_samples = updated_annotation_samples.exclude(individual__family__guid__in=exclude_families)
        if is_sv:
            updated_annotation_samples = updated_annotation_samples.filter(sample_type=data_type.split('_')[1])

        variant_models = get_saved_variants(
            genome_version, dataset_type=dataset_type,
            family_guids=updated_annotation_samples.values_list('individual__family__guid', flat=True).distinct(),
        )

        if not variant_models:
            logger.info('No additional saved variants to update')
            return

        variants_by_id = defaultdict(list)
        for v in variant_models:
            variants_by_id[v.variant_id].append(v)

        logger.info(f'Reloading shared annotations for {len(variant_models)} {data_type} {genome_version} saved variants ({len(variants_by_id)} unique)')

        updated_variants_by_id = {
            variant_id: {k: v for k, v in variant.items() if k not in {'familyGuids', 'genotypes', 'genotypeFilters'}}
            for variant_id, variant in (updated_variants_by_id or {}).items()
        }
        fetch_variant_ids = sorted(set(variants_by_id.keys()) - set(updated_variants_by_id.keys()))
        if fetch_variant_ids:
            if not is_sv:
                fetch_variant_ids = [parse_valid_variant_id(variant_id) for variant_id in fetch_variant_ids]
            for i in range(0, len(fetch_variant_ids), MAX_LOOKUP_VARIANTS):
                updated_variants = hail_variant_multi_lookup(USER_EMAIL, fetch_variant_ids[i:i+MAX_LOOKUP_VARIANTS], data_type, genome_version)
                logger.info(f'Fetched {len(updated_variants)} additional variants')
                updated_variants_by_id.update({variant['variantId']: variant for variant in updated_variants})

        updated_variant_models = []
        for variant_id, variant in updated_variants_by_id.items():
            for variant_model in variants_by_id[variant_id]:
                variant_model.saved_variant_json.update(variant)
                updated_variant_models.append(variant_model)

        SavedVariant.objects.bulk_update(updated_variant_models, ['saved_variant_json'], batch_size=10000)
        logger.info(f'Updated {len(updated_variant_models)} saved variants')


reload_shared_variant_annotations = Command._reload_shared_variant_annotations
