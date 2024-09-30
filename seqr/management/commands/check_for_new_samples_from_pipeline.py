from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.db.models.functions import JSONObject
import json
import logging
import re

from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Family, Sample, SavedVariant
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.file_utils import file_iter, list_files
from seqr.utils.search.add_data_utils import notify_search_data_loaded
from seqr.utils.search.utils import parse_valid_variant_id
from seqr.utils.search.hail_search_utils import hail_variant_multi_lookup, search_data_type
from seqr.views.utils.airtable_utils import AirtableSession, LOADABLE_PDO_STATUSES, AVAILABLE_PDO_STATUS
from seqr.views.utils.dataset_utils import match_and_update_search_samples
from seqr.views.utils.permissions_utils import is_internal_anvil_project, project_has_anvil
from seqr.views.utils.variant_utils import reset_cached_search_results, update_projects_saved_variant_json, \
    get_saved_variants
from settings import SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

logger = logging.getLogger(__name__)

GS_PATH_TEMPLATE = 'gs://seqr-hail-search-data/v3.1/{genome_version}/{dataset_type}/runs/{run_version}/_SUCCESS'
GS_PATH_FIELDS = ['genome_version', 'dataset_type', 'run_version']
GS_PATH_REGEX = GS_PATH_TEMPLATE.format(**{field: f'(?P<{field}>[^/]+)' for field in GS_PATH_FIELDS})

DATASET_TYPE_MAP = {'GCNV': Sample.DATASET_TYPE_SV_CALLS}
USER_EMAIL = 'manage_command'
MAX_LOOKUP_VARIANTS = 5000

PDO_COPY_FIELDS = [
    'PDO', 'PDOStatus', 'SeqrLoadingDate', 'GATKShortReadCallsetPath', 'SeqrProjectURL', 'TerraProjectURL',
    'SequencingProduct', 'PDOName', 'SequencingSubmissionDate', 'SequencingCompletionDate', 'CallsetRequestedDate',
    'CallsetCompletionDate', 'Project', 'Metrics Checked', 'gCNV_SV_CallsetPath', 'DRAGENShortReadCallsetPath',
]


class Command(BaseCommand):
    help = 'Check for newly loaded seqr samples'

    def add_arguments(self, parser):
        parser.add_argument('--genome_version')
        parser.add_argument('--dataset_type')
        parser.add_argument('--run-version')

    def handle(self, *args, **options):
        gs_path = GS_PATH_TEMPLATE.format(**{field: options[field] or '*' for field in GS_PATH_FIELDS})
        success_runs = {path: re.match(GS_PATH_REGEX, path).groupdict() for path in list_files(gs_path, user=None)}
        if not success_runs:
            user_args = [f'{k}={options[k]}' for k in GS_PATH_FIELDS if options[k]]
            raise CommandError(f'No successful runs found for {", ".join(user_args)}')

        loaded_runs = set(Sample.objects.filter(data_source__isnull=False).values_list('data_source', flat=True))
        new_runs = {path: run for path, run in success_runs.items() if run['run_version'] not in loaded_runs}
        if not new_runs:
            logger.info(f'Data already loaded for all {len(success_runs)} runs')
            return

        logger.info(f'Loading new samples from {len(success_runs)} run(s)')
        updated_families_by_data_type = defaultdict(set)
        updated_variants_by_data_type = defaultdict(dict)
        for path, run in new_runs.items():
            try:
                metadata_path = path.replace('_SUCCESS', 'metadata.json')
                data_type, updated_families, updated_variants_by_id = self._load_new_samples(metadata_path, **run)
                data_type_key = (data_type, run['genome_version'])
                updated_families_by_data_type[data_type_key].update(updated_families)
                updated_variants_by_data_type[data_type_key].update(updated_variants_by_id)
            except Exception as e:
                logger.error(f'Error loading {run["run_version"]}: {e}')

        # Reset cached results for all projects, as seqr AFs will have changed for all projects when new data is added
        reset_cached_search_results(project=None)

        for data_type_key, updated_families in updated_families_by_data_type.items():
            self._reload_shared_variant_annotations(
                *data_type_key, updated_variants_by_data_type[data_type_key], exclude_families=updated_families,
            )

        logger.info('DONE')

    @classmethod
    def _load_new_samples(cls, metadata_path, genome_version, dataset_type, run_version):
        dataset_type = DATASET_TYPE_MAP.get(dataset_type, dataset_type)

        logger.info(f'Loading new samples from {genome_version}/{dataset_type}: {run_version}')

        metadata = json.loads(next(line for line in file_iter(metadata_path)))
        families = Family.objects.filter(guid__in=metadata['family_samples'].keys())
        if len(families) < len(metadata['family_samples']):
            invalid = metadata['family_samples'].keys() - set(families.values_list('guid', flat=True))
            raise CommandError(f'Invalid families in run metadata {genome_version}/{dataset_type}: {run_version} - {", ".join(invalid)}')

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
            sample_data={'data_source': run_version, 'elasticsearch_index': ';'.join(metadata['callsets'])},
            sample_type=sample_type,
            dataset_type=dataset_type,
            user=None,
        )

        # Send loading notifications and update Airtable PDOs
        update_sample_data_by_project = {
            s['individual__family__project']: s for s in updated_samples.values('individual__family__project').annotate(
                samples=ArrayAgg(JSONObject(sample_id='sample_id', individual_id='individual_id')),
                family_guids=ArrayAgg('individual__family__guid', distinct=True),
            )
        }
        updated_project_families = []
        updated_families = set()
        split_project_pdos = {}
        session = AirtableSession(user=None, no_auth=True)
        for project, sample_ids in samples_by_project.items():
            project_sample_data = update_sample_data_by_project[project.id]
            is_internal = not project_has_anvil(project) or is_internal_anvil_project(project)
            notify_search_data_loaded(
                project, is_internal, dataset_type, sample_type, inactivated_sample_guids,
                updated_samples=project_sample_data['samples'], num_samples=len(sample_ids),
            )
            project_families = project_sample_data['family_guids']
            updated_families.update(project_families)
            updated_project_families.append((project.id, project.name, project.genome_version, project_families))
            if is_internal and dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
                split_project_pdos[project.name] = cls._update_pdos(session, project.guid, sample_ids)

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
                split_pdos = split_project_pdos.get(project)
                if split_pdos:
                    summary += f'\n\nSkipped samples in this project have been moved to {", ".join(split_pdos)}'
                safe_post_to_slack(
                    SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL,
                    f'The following {len(failures)} families failed {check.replace("_", " ")} in {project}:\n{summary}'
                )

        # Reload saved variant JSON
        updated_variants_by_id = update_projects_saved_variant_json(
            updated_project_families, user_email=USER_EMAIL, dataset_type=dataset_type)

        return search_data_type(dataset_type, sample_type), updated_families, updated_variants_by_id

    @staticmethod
    def _update_pdos(session, project_guid, sample_ids):
        airtable_samples = session.get_samples_for_matched_pdos(
            LOADABLE_PDO_STATUSES, pdo_fields=['PDOID'], project_guid=project_guid,
        )

        pdo_ids = set()
        skipped_pdo_samples = defaultdict(list)
        for record_id, sample in airtable_samples.items():
            pdo_id = sample['pdos'][0]['PDOID']
            if sample['sample_id'] in sample_ids:
                pdo_ids.add(pdo_id)
            else:
                skipped_pdo_samples[pdo_id].append(record_id)

        if pdo_ids:
            session.safe_patch_records_by_id('PDO', pdo_ids, {'PDOStatus': AVAILABLE_PDO_STATUS})

        skipped_pdo_samples = {
            pdo_id: sample_record_ids for pdo_id, sample_record_ids in skipped_pdo_samples.items() if pdo_id in pdo_ids
        }
        if not skipped_pdo_samples:
            return []

        pdos_to_create = {
            f"{pdo.pop('PDO')}_sr": (record_id, pdo) for record_id, pdo in session.fetch_records(
                'PDO', fields=PDO_COPY_FIELDS, or_filters={'RECORD_ID()': list(skipped_pdo_samples.keys())}
            ).items()
        }

        # Create PDOs and then update Samples with new PDOs
        # Does not create PDOs with Samples directly as that would not remove Samples from old PDOs
        new_pdos = session.safe_create_records('PDO', [
            {'PDO': pdo_name, **pdo} for pdo_name, (_, pdo) in pdos_to_create.items()
        ])
        pdo_id_map = {pdos_to_create[record['fields']['PDO']][0]: record['id'] for record in new_pdos}
        for pdo_id, sample_record_ids in skipped_pdo_samples.items():
            new_pdo_id = pdo_id_map.get(pdo_id)
            if new_pdo_id:
                session.safe_patch_records_by_id('Samples', sample_record_ids, {'PDOID': [new_pdo_id]})

        return sorted(pdos_to_create.keys())

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

        variant_type_summary = f'{data_type} {genome_version} saved variants'
        if not variant_models:
            logger.info(f'No additional {variant_type_summary} to update')
            return

        variants_by_id = defaultdict(list)
        for v in variant_models:
            variants_by_id[v.variant_id].append(v)

        logger.info(f'Reloading shared annotations for {len(variant_models)} {variant_type_summary} ({len(variants_by_id)} unique)')

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
        logger.info(f'Updated {len(updated_variant_models)} {variant_type_summary}')


reload_shared_variant_annotations = Command._reload_shared_variant_annotations
