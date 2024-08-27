from collections import defaultdict, OrderedDict
from django.contrib.auth.models import User
from django.db.models import F

from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Sample, Individual, Project
from seqr.utils.communication_utils import send_project_notification, safe_post_to_slack
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.search.utils import backend_specific_call
from seqr.utils.search.elasticsearch.es_utils import validate_es_index_metadata_and_get_samples
from seqr.views.utils.airtable_utils import AirtableSession, ANVIL_REQUEST_TRACKING_TABLE
from seqr.views.utils.dataset_utils import match_and_update_search_samples, load_mapping_file
from seqr.views.utils.export_utils import write_multiple_files_to_gs
from seqr.views.utils.permissions_utils import is_internal_anvil_project, project_has_anvil
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, BASE_URL, ANVIL_UI_URL, \
    SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL

logger = SeqrLogger(__name__)

SEQR_V3_PEDIGREE_GS_PATH = 'gs://seqr-loading-temp/v3.1'


def _hail_backend_error(*args, **kwargs):
    raise ValueError('Adding samples is disabled for the hail backend')


def add_new_es_search_samples(request_json, project, user, notify=False, expected_families=None):
    dataset_type = request_json.get('datasetType')
    if dataset_type not in Sample.DATASET_TYPE_LOOKUP:
        raise ValueError(f'Invalid dataset type "{dataset_type}"')

    sample_ids, sample_type, sample_data = backend_specific_call(
        validate_es_index_metadata_and_get_samples,
        _hail_backend_error,
    )(request_json, project)
    if not sample_ids:
        raise ValueError('No samples found. Make sure the specified caller type is correct')

    sample_id_to_individual_id_mapping = load_mapping_file(
        request_json['mappingFilePath'], user) if request_json.get('mappingFilePath') else {}
    ignore_extra_samples = request_json.get('ignoreExtraSamplesInCallset')
    sample_project_tuples = [(sample_id, project.name) for sample_id in sample_ids]
    updated_samples, inactivated_sample_guids, num_skipped, updated_family_guids = match_and_update_search_samples(
        projects=[project],
        user=user,
        sample_project_tuples=sample_project_tuples,
        sample_data=sample_data,
        sample_type=sample_type,
        dataset_type=dataset_type,
        expected_families=expected_families,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        raise_unmatched_error_template=None if ignore_extra_samples else 'Matches not found for sample ids: {sample_ids}. Uploading a mapping file for these samples, or select the "Ignore extra samples in callset" checkbox to ignore.'
    )

    if notify:
        num_samples = len(sample_ids) - num_skipped
        updated_sample_data = updated_samples.values('sample_id', 'individual_id')
        notify_search_data_loaded(project, dataset_type, sample_type, inactivated_sample_guids, updated_sample_data, num_samples)

    return inactivated_sample_guids, updated_family_guids, updated_samples


def notify_search_data_loaded(project, dataset_type, sample_type, inactivated_sample_guids, updated_samples, num_samples):
    is_internal = not project_has_anvil(project) or is_internal_anvil_project(project)

    previous_loaded_individuals = set(Sample.objects.filter(guid__in=inactivated_sample_guids).values_list('individual_id', flat=True))
    new_sample_ids = [sample['sample_id'] for sample in updated_samples if sample['individual_id'] not in previous_loaded_individuals]

    url = f'{BASE_URL}project/{project.guid}/project_page'
    msg_dataset_type = '' if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS else f' {dataset_type}'
    sample_id_list = f'\n```{", ".join(sorted(new_sample_ids))}```' if is_internal else ''
    num_new_samples = len(new_sample_ids)
    sample_summary = f'{num_new_samples} new {sample_type}{msg_dataset_type} samples'
    summary_message = f'{sample_summary} are loaded in {url}{sample_id_list}'

    safe_post_to_slack(
        SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL if is_internal else SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL,
        summary_message)

    project_link = f'<a href={url}>{project.name}</a>'
    if is_internal:
        email = f'This is to notify you that {sample_summary} have been loaded in seqr project {project_link}'
    else:
        AirtableSession(user=None, base=AirtableSession.ANVIL_BASE, no_auth=True).safe_patch_records(
            ANVIL_REQUEST_TRACKING_TABLE, max_records=1,
            record_or_filters={'Status': ['Loading', 'Loading Requested']},
            record_and_filters={'AnVIL Project URL': url},
            update={'Status': 'Available in Seqr'},
        )
        workspace_name = f'{project.workspace_namespace}/{project.workspace_name}'
        reload_summary = f' and {num_samples - num_new_samples} re-loaded samples' if num_samples > num_new_samples else ''
        email = '\n'.join([
            f'We are following up on the request to load data from AnVIL on {project.created_date.date().strftime("%B %d, %Y")}.',
            f'We have loaded {sample_summary}{reload_summary} from the AnVIL workspace <a href={ANVIL_UI_URL}#workspaces/{workspace_name}>{workspace_name}</a> to the corresponding seqr project {project_link}.',
            'Let us know if you have any questions.',
        ])

    send_project_notification(
        project,
        notification=f'Loaded {sample_summary}',
        email=email,
        subject='New data available in seqr',
    )
    return is_internal


def prepare_data_loading_request(projects: list[Project], sample_type: str, dataset_type: str, genome_version: str,
                                 data_path: str, user: User, individual_ids: list[str] = None):
    variables = {
        'projects_to_run': sorted([p.guid for p in projects]),
        'callset_path': data_path,
        'sample_type': sample_type,
        'dataset_type': _dag_dataset_type(sample_type, dataset_type),
        'reference_genome': GENOME_VERSION_LOOKUP[genome_version],
    }
    gs_path = _get_gs_pedigree_path(genome_version, sample_type, dataset_type)
    _upload_data_loading_files(projects, user, gs_path, individual_ids)
    return variables, gs_path


def _dag_dataset_type(sample_type: str, dataset_type: str):
    return 'GCNV' if dataset_type == Sample.DATASET_TYPE_SV_CALLS and sample_type == Sample.SAMPLE_TYPE_WES \
        else dataset_type


def _get_gs_pedigree_path(genome_version: str, sample_type: str, dataset_type: str):
    return f'{SEQR_V3_PEDIGREE_GS_PATH}/{GENOME_VERSION_LOOKUP[genome_version]}/{dataset_type}/pedigrees/{sample_type}/'


def _upload_data_loading_files(projects: list[Project], user: User, gs_path: str, individual_ids: list[str]):
    file_annotations = OrderedDict({
        'Project_GUID': F('family__project__guid'), 'Family_GUID': F('family__guid'),
        'Family_ID': F('family__family_id'),
        'Individual_ID': F('individual_id'),
        'Paternal_ID': F('father__individual_id'), 'Maternal_ID': F('mother__individual_id'), 'Sex': F('sex'),
    })
    annotations = {'project': F('family__project__guid'), **file_annotations}
    individual_filter = {'id__in': individual_ids} if individual_ids else {'family__project__in': projects}
    data = Individual.objects.filter(**individual_filter).order_by('family_id', 'individual_id').values(
        **dict(annotations))

    data_by_project = defaultdict(list)
    for row in data:
        data_by_project[row.pop('project')].append(row)

    header = list(file_annotations.keys())
    files = [(f'{project_guid}_pedigree', header, rows) for project_guid, rows in data_by_project.items()]

    try:
        write_multiple_files_to_gs(files, gs_path, user, file_format='tsv')
    except Exception as e:
        logger.error(f'Uploading Pedigrees to Google Storage failed. Errors: {e}', user, detail={
            project: rows for project, _, rows in files
        })
