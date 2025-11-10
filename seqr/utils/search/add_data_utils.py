from collections import defaultdict, OrderedDict
from django.contrib.auth.models import User
from django.db.models import F
import json
import requests

from reference_data.models import GeneInfo, GENOME_VERSION_LOOKUP
from seqr.models import Sample, Individual, Project
from seqr.utils.communication_utils import send_project_notification, safe_post_to_slack
from seqr.utils.file_utils import does_file_exist
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.middleware import ErrorsWarningsException
from seqr.views.utils.airtable_utils import AirtableSession, ANVIL_REQUEST_TRACKING_TABLE
from seqr.views.utils.export_utils import write_multiple_files
from seqr.views.utils.json_utils import _to_title_case
from seqr.views.utils.pedigree_info_utils import JsonConstants
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, BASE_URL, ANVIL_UI_URL, PIPELINE_RUNNER_SERVER, \
    SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, LOADING_DATASETS_DIR

logger = SeqrLogger(__name__)


def basic_notify_search_data_loaded(project, dataset_type, sample_type, new_samples, email_template=None, is_internal=True):
    msg_dataset_type = '' if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS else f' {dataset_type}'
    num_new_samples = len(new_samples)
    sample_summary = f'{num_new_samples} new {sample_type}{msg_dataset_type} samples'

    return send_project_notification(
        project,
        notification=sample_summary,
        email_template=email_template,
        subject=f'New {sample_type}{msg_dataset_type} data available in seqr',
        slack_channel=SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL if is_internal else SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL,
        slack_detail=', '.join(sorted(new_samples)) if is_internal else None,
    )


def notify_search_data_loaded(project, is_internal, dataset_type, sample_type, new_samples, num_samples):
    if is_internal:
        email_template = None
    else:
        workspace_name = f'{project.workspace_namespace}/{project.workspace_name}'
        num_new_samples = len(new_samples)
        reload_summary = f' and {num_samples - num_new_samples} re-loaded samples' if num_samples > num_new_samples else ''
        email_template = '\n'.join([
            f'We are following up on the request to load data from AnVIL on {project.created_date.date().strftime("%B %d, %Y")}.',
            f'We have loaded {{notification}}{reload_summary} from the AnVIL workspace <a href={ANVIL_UI_URL}#workspaces/{workspace_name}>{workspace_name}</a> to the corresponding seqr project {{project_link}}.',
            'Let us know if you have any questions.',
        ])

    basic_notify_search_data_loaded(
        project, dataset_type, sample_type, new_samples, email_template=email_template, is_internal=is_internal,
    )

    if not is_internal:
        update_airtable_loading_tracking_status(project, 'Available in Seqr')

def update_airtable_loading_tracking_status(project, status, additional_update=None):
    AirtableSession(user=None, base=AirtableSession.ANVIL_BASE, no_auth=True).safe_patch_records(
        ANVIL_REQUEST_TRACKING_TABLE, max_records=1,
        record_or_filters={'Status': ['Loading', 'Loading Requested']},
        record_and_filters={'AnVIL Project URL': f'{BASE_URL}project/{project.guid}/project_page'},
        update={'Status': status, **(additional_update or {})},
    )

def trigger_delete_families_search(project, family_guids, user=None):
    search_samples = Sample.objects.filter(is_active=True, individual__family__guid__in=family_guids)
    info = []
    if search_samples:
        updated_families = search_samples.values_list("individual__family__family_id", flat=True).distinct()
        family_summary = ", ".join(sorted(updated_families))
        num_updated = search_samples.update(is_active=False)
        message = f'Disabled search for {num_updated} samples in the following {len(updated_families)} families: {family_summary}'
        info.append(message)
        logger.info(message, user)

    variables = {'project_guid': project.guid, 'family_guids': family_guids}
    _enqueue_pipeline_request('delete_families', variables, user)
    info.append('Triggered delete family data')
    return info

def trigger_rebuild_gt_stats(project, user):
    logger.info(f'Triggering rebuild_gt_stats for {project.guid}', user)
    _enqueue_pipeline_request('rebuild_gt_stats', {'project_guids': [project.guid]}, user, raise_error=False)

def trigger_data_loading(projects: list[Project], individual_ids: list[int], sample_type: str, dataset_type: str,
                         genome_version: str, data_path: str, user: User, raise_error: bool = False, skip_expect_tdr_metrics: bool = True,
                         skip_check_sex_and_relatedness: bool = True, vcf_sample_id_map=None,
                         success_message: str = None,  error_message: str = None, success_slack_channel: str = SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL):
    variables = {
        'projects_to_run': sorted([p.guid for p in projects]) if projects else None,
        'dataset_type': _loading_dataset_type(sample_type, dataset_type),
        'reference_genome': GENOME_VERSION_LOOKUP[genome_version],
        'callset_path': data_path,
        'sample_type': sample_type,
    }
    bool_variables = {
        'skip_check_sex_and_relatedness': skip_check_sex_and_relatedness,
        'skip_expect_tdr_metrics': skip_expect_tdr_metrics,
    }
    variables.update({k: v for k, v in bool_variables.items() if v})
    file_path = _get_pedigree_path(genome_version, sample_type, dataset_type)
    _upload_data_loading_files(individual_ids, vcf_sample_id_map or {}, user, file_path, raise_error)
    _write_gene_id_file(user)

    error = _enqueue_pipeline_request('loading_pipeline', variables, user, raise_error, log_error=False)
    if error:
        safe_post_to_slack(
            SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL,
            f'{error_message}: {error}\nLoading pipeline should be triggered with:\n```{json.dumps(variables, indent=4)}```',
        )

    success = not error
    if success_message and (success or success_slack_channel != SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL):
        safe_post_to_slack(success_slack_channel, '\n\n'.join([
            success_message,
            f'Pedigree files have been uploaded to {file_path}',
            f'Loading pipeline is triggered with:\n```{json.dumps(variables, indent=4)}```',
        ]))

    return success


def _enqueue_pipeline_request(name: str, variables: dict, user: User, raise_error: bool = True, log_error: bool = True):
    response = None
    error = None
    try:
        response = requests.post(f'{PIPELINE_RUNNER_SERVER}/{name}_enqueue', json=variables, timeout=60)
        response.raise_for_status()
        logger.info(f'Triggered {_to_title_case(name)}', user, detail=variables)
    except requests.RequestException as e:
        error = str(e)
        if response is not None and response.status_code == 409:
            error = 'Loading pipeline is already running. Wait for it to complete and resubmit'
            e = ErrorsWarningsException([error])
        if raise_error:
            raise e
        else:
            log_func = logger.error if log_error else logger.warning
            log_func(f'Error Triggering {_to_title_case(name)}: {error}', user, detail=variables)
    return error


def _loading_dataset_type(sample_type: str, dataset_type: str):
    return 'GCNV' if dataset_type == Sample.DATASET_TYPE_SV_CALLS and sample_type == Sample.SAMPLE_TYPE_WES \
        else dataset_type


def _upload_data_loading_files(individual_ids: list[int], vcf_sample_id_map: dict, user: User, file_path: str, raise_error: bool):
    file_annotations = OrderedDict({
        'Project_GUID': F('family__project__guid'), 'Family_GUID': F('family__guid'),
        'Family_ID': F('family__family_id'),
        'Individual_ID': F('individual_id'),
        'Paternal_ID': F('father__individual_id'), 'Maternal_ID': F('mother__individual_id'), 'Sex': F('sex'),
    })
    annotations = {'project': F('family__project__guid'), **file_annotations}
    data = Individual.objects.filter(id__in=individual_ids).order_by('family_id', 'individual_id').values(
        **dict(annotations))

    data_by_project = defaultdict(list)
    for row in data:
        data_by_project[row.pop('project')].append(row)
        if vcf_sample_id_map:
            row['VCF_ID'] = vcf_sample_id_map.get(row['Individual_ID'])

    header = list(file_annotations.keys())
    if vcf_sample_id_map:
        header.append('VCF_ID')
    files = [(f'{project_guid}_pedigree', header, rows) for project_guid, rows in data_by_project.items()]

    try:
        write_multiple_files(files, file_path, user, file_format='tsv')
    except Exception as e:
        logger.error(f'Uploading Pedigrees failed. Errors: {e}', user, detail={
            project: rows for project, _, rows in files
        })
        if raise_error:
            raise e


def _write_gene_id_file(user):
    file_name = 'db_id_to_gene_id'
    if does_file_exist(f'{LOADING_DATASETS_DIR}/{file_name}.csv.gz'):
        return

    gene_data_loaded = (GeneInfo.objects.filter(gencode_release=int(GeneInfo.CURRENT_VERSION)).exists() and
                        GeneInfo.objects.filter(gencode_release=int(GeneInfo.ALL_GENCODE_VERSIONS[-1])).exists())
    if not gene_data_loaded:
        raise ValueError(
            'Gene reference data is not yet loaded. If this is a new seqr installation, wait for the initial data load '
            'to complete. If this is an existing installation, see the documentation for updating data in seqr.'
        )
    gene_data = GeneInfo.objects.all().values('gene_id', db_id=F('id')).order_by('id')
    file_config = (file_name, ['db_id', 'gene_id'], gene_data)
    write_multiple_files([file_config], LOADING_DATASETS_DIR, user, file_format='csv', gzip_file=True)


def _get_pedigree_path(genome_version: str, sample_type: str, dataset_type: str):
    loading_dataset_type = _loading_dataset_type(sample_type, dataset_type)
    return f'{LOADING_DATASETS_DIR}/{GENOME_VERSION_LOOKUP[genome_version]}/{loading_dataset_type}/pedigrees/{sample_type}'


def get_missing_family_samples(expected_sample_set, record_family_ids, previous_loaded_individuals):
    families = set(record_family_ids.values())
    missing_samples_by_family = defaultdict(set)
    for loaded_individual in previous_loaded_individuals:
        individual_id = loaded_individual[JsonConstants.INDIVIDUAL_ID_COLUMN]
        family_id = loaded_individual[JsonConstants.FAMILY_ID_COLUMN]
        if family_id in families and individual_id not in expected_sample_set:
            missing_samples_by_family[family_id].add(individual_id)

    return missing_samples_by_family


def get_loaded_individual_ids(record_family_ids, previous_loaded_individuals):
    families = set(record_family_ids.values())
    return [
        i['individual_id'] for i in previous_loaded_individuals if i[JsonConstants.FAMILY_ID_COLUMN] in families
    ]
