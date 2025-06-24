import os
from collections import defaultdict

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand, CommandError
import json
import logging
import re

from reference_data.models import GENOME_VERSION_LOOKUP, GENOME_VERSION_GRCh38
from seqr.models import Family, Sample, SavedVariant, Project, Individual
from seqr.utils.communication_utils import safe_post_to_slack, send_project_email
from seqr.utils.file_utils import file_iter, list_files, is_google_bucket_file_path
from seqr.utils.search.add_data_utils import notify_search_data_loaded, update_airtable_loading_tracking_status
from seqr.utils.search.utils import parse_valid_variant_id
from seqr.utils.search.hail_search_utils import hail_variant_multi_lookup, search_data_type
from seqr.utils.xpos_utils import get_xpos, CHROMOSOMES, MIN_POS, MAX_POS
from seqr.views.utils.airtable_utils import AirtableSession, LOADABLE_PDO_STATUSES, AVAILABLE_PDO_STATUS
from seqr.views.utils.dataset_utils import match_and_update_search_samples
from seqr.views.utils.export_utils import write_multiple_files
from seqr.views.utils.permissions_utils import is_internal_anvil_project, project_has_anvil
from seqr.views.utils.variant_utils import reset_cached_search_results, update_projects_saved_variant_json, \
    get_saved_variants
from settings import SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, HAIL_SEARCH_DATA_DIR, ANVIL_UI_URL, \
    SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL

logger = logging.getLogger(__name__)

CLICKHOUSE_MIGRATION_SENTINEL = 'hail_search_to_clickhouse_migration'
RUN_FILE_PATH_TEMPLATE = '{data_dir}/{genome_version}/{dataset_type}/runs/{run_version}/{file_name}'
SUCCESS_FILE_NAME = '_SUCCESS'
VALIDATION_ERRORS_FILE_NAME = 'validation_errors.json'
ERRORS_REPORTED_FILE_NAME = '_ERRORS_REPORTED'
RUN_PATH_FIELDS = ['genome_version', 'dataset_type', 'run_version', 'file_name']

DATASET_TYPE_MAP = {'GCNV': Sample.DATASET_TYPE_SV_CALLS}
USER_EMAIL = 'manage_command'
MAX_LOOKUP_VARIANTS = 1000
MAX_RELOAD_VARIANTS = 100000
RELATEDNESS_CHECK_NAME = 'relatedness_check'

PDO_COPY_FIELDS = [
    'PDO', 'PDOStatus', 'SeqrLoadingDate', 'GATKShortReadCallsetPath', 'SeqrProjectURL', 'TerraProjectURL',
    'SequencingProduct', 'PDOName', 'SequencingSubmissionDate', 'SequencingCompletionDate', 'CallsetRequestedDate',
    'CallsetCompletionDate', 'Project', 'Metrics Checked', 'gCNV_SV_CallsetPath', 'DRAGENShortReadCallsetPath',
]

QC_FILTER_FLAG_COL_MAP = {
    'callrate': 'filtered_callrate',
    'contamination': 'contamination_rate',
    'coverage_exome': 'percent_bases_at_20x',
    'coverage_genome': 'mean_coverage'
}

class Command(BaseCommand):
    help = 'Check for newly loaded seqr samples'

    def add_arguments(self, parser):
        parser.add_argument('--genome_version')
        parser.add_argument('--dataset_type')
        parser.add_argument('--run-version')

    def handle(self, *args, **options):
        runs = self._get_runs(**options)

        success_run_dirs = [run_dir for run_dir, run_details in runs.items() if SUCCESS_FILE_NAME in run_details['files']]
        if success_run_dirs:
            self._load_success_runs(runs, success_run_dirs)
        if not success_run_dirs:
            user_args = [f'{k}={options.get(k)}' for k in RUN_PATH_FIELDS if options.get(k)]
            if user_args:
                raise CommandError(f'No successful runs found for {", ".join(user_args)}')
            else:
                logger.info('No loaded data available')

        self._report_validation_errors(runs)
        logger.info('DONE')


    def _load_success_runs(self, runs, success_run_dirs):
        loaded_runs = set(Sample.objects.filter(data_source__isnull=False).values_list('data_source', flat=True))
        new_runs = {
            run_dir: run_details for run_dir, run_details in runs.items()
            if run_dir in success_run_dirs and run_details['run_version'] not in loaded_runs
        }
        if not new_runs:
            logger.info(f'Data already loaded for all {len(success_run_dirs)} runs')
            return

        logger.info(f'Loading new samples from {len(success_run_dirs)} run(s)')
        updated_families_by_data_type = defaultdict(set)
        updated_variants_by_data_type = defaultdict(dict)
        for run_dir, run_details in new_runs.items():
            try:
                if CLICKHOUSE_MIGRATION_SENTINEL in run_details["run_version"]:
                    logging.info(f'Skipping ClickHouse migration {run_details["genome_version"]}/{run_details["dataset_type"]}: {run_details["run_version"]}')
                    continue
                metadata_path = os.path.join(run_dir, 'metadata.json')
                data_type, updated_families, updated_variants_by_id = self._load_new_samples(metadata_path, **run_details)
                data_type_key = (data_type, run_details['genome_version'])
                updated_families_by_data_type[data_type_key].update(updated_families)
                updated_variants_by_data_type[data_type_key].update(updated_variants_by_id)
            except Exception as e:
                logger.error(f'Error loading {run_details["run_version"]}: {e}')

        # Reset cached results for all projects, as seqr AFs will have changed for all projects when new data is added
        reset_cached_search_results(project=None)

        for data_type_key, updated_families in updated_families_by_data_type.items():
            try:
                self._reload_shared_variant_annotations(
                    *data_type_key, updated_variants_by_data_type[data_type_key], exclude_families=updated_families,
                )
            except Exception as e:
                logger.error(f'Error reloading shared annotations for {"/".join(data_type_key)}: {e}')

    @classmethod
    def _get_runs(cls, **kwargs):
        path = cls._run_path(lambda field: kwargs.get(field, '*') or '*')
        path_regex = cls._run_path(lambda field: f'(?P<{field}>[^/]+)')

        runs = defaultdict(lambda: {'files': set()})
        for path in list_files(path, user=None):
            run_dirname = os.path.dirname(path)
            match_dict = re.match(f'{path_regex}?', path).groupdict()
            file_name = match_dict.pop('file_name')
            if file_name:
                runs[run_dirname]['files'].add(file_name)
                runs[run_dirname].update(match_dict)

        return runs

    @staticmethod
    def _run_path(get_field_format):
        return RUN_FILE_PATH_TEMPLATE.format(
            data_dir=HAIL_SEARCH_DATA_DIR,
            **{field: get_field_format(field) for field in RUN_PATH_FIELDS}
        )

    @classmethod
    def _report_validation_errors(cls, runs) -> None:
        for run_dir, run_details in sorted(runs.items()):
            files = run_details['files']
            if ERRORS_REPORTED_FILE_NAME in files:
                continue
            if VALIDATION_ERRORS_FILE_NAME in files:
                file_path = os.path.join(run_dir, VALIDATION_ERRORS_FILE_NAME)
                error_summary = json.loads(next(line for line in file_iter(file_path)))
                error_messages = error_summary.get('error_messages')
                project_guids = error_summary.get('project_guids') or []
                project = Project.objects.filter(guid__in=project_guids).first() if len(project_guids) == 1 else None
                if error_messages and project and not cls._is_internal_project(project):
                    cls._report_anvil_project_validation_error(project, error_messages)
                else:
                    cls._report_internal_validation_error(
                        run_details, file_path, project_guids, error_messages or json.dumps(error_summary),
                    )
                write_multiple_files([(ERRORS_REPORTED_FILE_NAME, [], [])], run_dir, user=None, file_format=None)

    @classmethod
    def _report_internal_validation_error(cls, run_details, file_path, project_guids, error_messages):
        summary = [
            'Callset Validation Failed',
            f'*Projects:* {project_guids or "MISSING FROM ERROR REPORT"}',
            f'*Reference Genome:* {run_details["genome_version"]}',
            f'*Dataset Type:* {run_details["dataset_type"]}',
            f'*Run ID:* {run_details["run_version"]}',
            f'*Validation Errors:* {error_messages}',
        ]
        if is_google_bucket_file_path(file_path):
            summary.append(f'See more at https://storage.cloud.google.com/{file_path[5:]}')
        safe_post_to_slack(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, '\n'.join(summary))

    @classmethod
    def _report_anvil_project_validation_error(cls, project, error_messages):
        workspace_name = f'{project.workspace_namespace}/{project.workspace_name}'
        error_list = [f'- {error}' for error in error_messages]
        email_body = '\n'.join([
            f'We are following up on the request to load data from AnVIL workspace '
            f'<a href={ANVIL_UI_URL}#workspaces/{workspace_name}>{workspace_name}</a> on {project.created_date.date().strftime("%B %d, %Y")}. '
            f'This request could not be loaded due to the following error(s):'
        ] + error_list + [
            'These errors often occur when a joint called VCF is not created in a supported manner. Please see our '
            '<a href=https://storage.googleapis.com/seqr-reference-data/seqr-vcf-info.pdf>documentation</a> for more '
            'information about supported calling pipelines and file formats. If you believe this error is incorrect '
            'and would like to request a manual review, please respond to this email.',
        ])
        recipients = send_project_email(project, email_body, 'Error loading seqr data')

        slack_message = '\n'.join([
            f'Request to load data from *{workspace_name}* failed with the following error(s):',
        ] + error_list + [
            f'The following users have been notified: {", ".join(recipients.values_list("email", flat=True))}'
        ])
        safe_post_to_slack(SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, slack_message)

        update_airtable_loading_tracking_status(project, 'Loading request canceled', {
            'Notes': 'Callset validation failed',
        })

    @classmethod
    def _load_new_samples(cls, metadata_path, genome_version, dataset_type, run_version, **kwargs):
        dataset_type = DATASET_TYPE_MAP.get(dataset_type, dataset_type)

        logger.info(f'Loading new samples from {genome_version}/{dataset_type}: {run_version}')

        metadata = json.loads(next(line for line in file_iter(metadata_path)))
        run_family_guids = set(metadata['family_samples'].keys())
        families = Family.objects.filter(guid__in=run_family_guids)
        if len(families) < len(run_family_guids):
            invalid = run_family_guids - set(families.values_list('guid', flat=True))
            raise CommandError(f'Invalid families in run metadata {genome_version}/{dataset_type}: {run_version} - {", ".join(invalid)}')

        family_project_map = {f.guid: f.project for f in families.select_related('project')}
        families_by_project = defaultdict(list)
        samples_by_project = defaultdict(list)
        for family_guid, sample_ids in metadata['family_samples'].items():
            project = family_project_map[family_guid]
            families_by_project[project].append(family_guid)
            samples_by_project[project] += sample_ids

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
        new_samples, *args = match_and_update_search_samples(
            projects=samples_by_project.keys(),
            sample_project_tuples=sample_project_tuples,
            sample_data={'data_source': run_version, 'elasticsearch_index': ';'.join(metadata['callsets'])},
            sample_type=sample_type,
            dataset_type=dataset_type,
            user=None,
        )

        new_samples_by_project = dict(new_samples.values('individual__family__project').annotate(
            samples=ArrayAgg('sample_id', distinct=True),
        ).values_list('individual__family__project', 'samples'))

        split_project_pdos = cls._report_loading_success(
            dataset_type, sample_type, run_version, samples_by_project, new_samples_by_project,
        )
        try:
            failed_family_guids = cls._report_loading_failures(metadata, split_project_pdos)
            run_family_guids.update(failed_family_guids)
        except Exception as e:
            logger.error(f'Error reporting loading failure for {run_version}: {e}')

        # Update sample qc
        if 'sample_qc' in metadata:
            try:
                cls._update_individuals_sample_qc(sample_type, run_family_guids, metadata['sample_qc'])
            except Exception as e:
                logger.error(f'Error updating individuals sample qc {run_version}: {e}')

        # Reload saved variant JSON
        updated_variants_by_id = update_projects_saved_variant_json([
            (project.id, project.name, project.genome_version, families) for project, families in families_by_project.items()
        ], user_email=USER_EMAIL, dataset_type=dataset_type)

        return search_data_type(dataset_type, sample_type), set(family_project_map.keys()), updated_variants_by_id

    @classmethod
    def _is_internal_project(cls, project):
        return not project_has_anvil(project) or is_internal_anvil_project(project)

    @classmethod
    def _report_loading_success(cls, dataset_type, sample_type, run_version, samples_by_project, new_samples_by_project):
        split_project_pdos = {}
        session = AirtableSession(user=None, no_auth=True) if AirtableSession.is_airtable_enabled() else None
        for project, sample_ids in samples_by_project.items():
            try:
                is_internal = cls._is_internal_project(project)
                notify_search_data_loaded(
                    project, is_internal, dataset_type, sample_type, new_samples_by_project.get(project.id, []),
                    num_samples=len(sample_ids),
                )
                if session and is_internal and dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
                    split_project_pdos[project.name] = cls._update_pdos(session, project.guid, sample_ids)
            except Exception as e:
                logger.error(f'Error reporting loading success for project {project.name} in {run_version}: {e}')

        return split_project_pdos

    @classmethod
    def _report_loading_failures(cls, metadata, split_project_pdos):
        # Send failure notifications
        relatedness_check_file_path = metadata.get('relatedness_check_file_path')
        failed_family_samples = metadata.get('failed_family_samples', {})
        failed_families_by_guid = {f['guid']: f for f in Family.objects.filter(
            guid__in={family for families in failed_family_samples.values() for family in families}
        ).values('guid', 'family_id', 'project__name')}
        if failed_families_by_guid:
            Family.bulk_update(
                user=None, update_json={'analysis_status': Family.ANALYSIS_STATUS_LOADING_FAILED},
                guid__in=failed_families_by_guid, analysis_status=Family.ANALYSIS_STATUS_WAITING_FOR_DATA
            )
        failures_by_project_check = defaultdict(lambda: defaultdict(list))
        for check, check_failures in failed_family_samples.items():
            for family_guid, failure_data in check_failures.items():
                family = failed_families_by_guid[family_guid]
                failures_by_project_check[family['project__name']][check].append(
                    f'- {family["family_id"]}: {"; ".join(failure_data["reasons"])}'
                )
        for project, failures_by_check in failures_by_project_check.items():
            messages = [f'Encountered the following errors loading {project}:']
            for check, failures in failures_by_check.items():
                summary = '\n'.join(sorted(failures))
                messages.append(f"The following {len(failures)} families failed {check.replace('_', ' ')}:\n{summary}")
                if check == RELATEDNESS_CHECK_NAME and relatedness_check_file_path:
                    downloadable_link = f'https://storage.cloud.google.com/{relatedness_check_file_path[5:]}'
                    messages.append(f'Relatedness check results: {downloadable_link}')

            split_pdos = split_project_pdos.get(project)
            if split_pdos:
                messages.append(f'Skipped samples in this project have been moved to {", ".join(split_pdos)}')
            safe_post_to_slack(
                SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, '\n\n'.join(messages),
            )
        return set(failed_families_by_guid.keys())

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
            {'PDO': pdo_name, **pdo, 'PDOStatus': 'PM team (Relatedness checks)'} for pdo_name, (_, pdo) in pdos_to_create.items()
        ])
        pdo_id_map = {pdos_to_create[record['fields']['PDO']][0]: record['id'] for record in new_pdos}
        for pdo_id, sample_record_ids in skipped_pdo_samples.items():
            new_pdo_id = pdo_id_map.get(pdo_id)
            if new_pdo_id:
                session.safe_patch_records_by_id('Samples', sample_record_ids, {'PDOID': [new_pdo_id]})

        return sorted(pdos_to_create.keys())

    @classmethod
    def _update_individuals_sample_qc(cls, sample_type, family_guids, sample_qc_map):
        individuals = Individual.objects.filter(individual_id__in=sample_qc_map.keys(), family__guid__in=family_guids)
        sample_individual_map = {i.individual_id: i for i in individuals}
        updated_individuals = []
        for individual_id, record in sample_qc_map.items():
            individual = sample_individual_map[individual_id]
            filter_flags = {}
            for flag in record['filter_flags']:
                flag = '{}_{}'.format(flag, 'exome' if sample_type.lower() == 'wes' else 'genome') if flag == 'coverage' else flag
                flag_col = QC_FILTER_FLAG_COL_MAP.get(flag, flag)
                filter_flags[flag] = record[flag_col]

            pop_platform_filters = {}
            for flag in record['qc_metrics_filters']:
                flag_col = 'sample_qc.{}'.format(flag)
                pop_platform_filters[flag] = record[flag_col]

            individual.filter_flags = filter_flags
            individual.pop_platform_filters = pop_platform_filters
            individual.population = record['qc_gen_anc'].upper()
            updated_individuals.append(individual)

        if updated_individuals:
            Individual.bulk_update_models(
                user=None,
                models=updated_individuals,
                fields=['filter_flags', 'pop_platform_filters', 'population'],
            )


    @classmethod
    def _reload_shared_variant_annotations(cls, data_type, genome_version, updated_variants_by_id=None, exclude_families=None, chromosomes=None):
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

        if updated_variants_by_id:
            fetched_variant_models = variant_models.filter(variant_id__in=updated_variants_by_id.keys())
            if fetched_variant_models:
                logger.info(f'Reloading shared annotations for {len(fetched_variant_models)} fetched {variant_type_summary}')
                for variant_model in fetched_variant_models:
                    updated_variant = {
                        k: v for k, v in updated_variants_by_id[variant_model.variant_id].items()
                        if k not in {'familyGuids', 'genotypes'}
                    }
                    variant_model.saved_variant_json.update(updated_variant)
                SavedVariant.bulk_update_models(None, fetched_variant_models, ['saved_variant_json'])

            variant_models = variant_models.exclude(variant_id__in=updated_variants_by_id.keys())

        chromosomes = cls._get_chroms_to_reload(chromosomes, dataset_type, genome_version, variant_models)
        if chromosomes is None:
            return

        for chrom in chromosomes:
            cls._reload_shared_variant_annotations_by_chrom(chrom, variant_models, data_type, genome_version, variant_type_summary)

    @staticmethod
    def _get_chroms_to_reload(chromosomes, dataset_type, genome_version, variant_models):
        if dataset_type != Sample.DATASET_TYPE_VARIANT_CALLS:
            return [None]
        if chromosomes:
            return chromosomes

        num_reload = variant_models.count()
        if genome_version == GENOME_VERSION_LOOKUP[GENOME_VERSION_GRCh38] and num_reload > MAX_RELOAD_VARIANTS:
            logger.info(f'Skipped reloading all {num_reload} saved variant annotations for {dataset_type} {genome_version}')
            return None

        return CHROMOSOMES

    @classmethod
    def _reload_shared_variant_annotations_by_chrom(cls, chrom, variant_models, data_type, genome_version, variant_type_summary):
        if chrom:
            variant_models = variant_models.filter(xpos__gte=get_xpos(chrom, MIN_POS), xpos__lte=get_xpos(chrom, MAX_POS))

        chrom_summary = f' in chromosome {chrom}' if chrom else ''
        if not variant_models:
            logger.info(f'No additional {variant_type_summary} to update{chrom_summary}')
            return

        variants_by_id = defaultdict(list)
        for v in variant_models:
            variants_by_id[v.variant_id].append(v)

        logger.info(f'Reloading shared annotations for {len(variant_models)} {variant_type_summary}{chrom_summary} ({len(variants_by_id)} unique)')

        variant_ids = sorted(variants_by_id.keys())
        if chrom:
            variant_ids = sorted([parse_valid_variant_id(variant_id) for variant_id in variant_ids])

        for i in range(0, len(variant_ids), MAX_LOOKUP_VARIANTS):
            updated_variants = hail_variant_multi_lookup(USER_EMAIL, variant_ids[i:i+MAX_LOOKUP_VARIANTS], data_type, genome_version)
            logger.info(f'Fetched {len(updated_variants)} additional variants{chrom_summary}')

            updated_variant_models = []
            for variant in updated_variants:
                for variant_model in variants_by_id[variant['variantId']]:
                    variant_model.saved_variant_json.update(variant)
                    updated_variant_models.append(variant_model)

            SavedVariant.bulk_update_models(None, updated_variant_models, ['saved_variant_json'])


reload_shared_variant_annotations = Command._reload_shared_variant_annotations
update_individuals_sample_qc = Command._update_individuals_sample_qc
get_pipeline_runs = Command._get_runs
