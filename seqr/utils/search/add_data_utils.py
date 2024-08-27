from seqr.models import Sample
from seqr.utils.communication_utils import send_project_notification, safe_post_to_slack
from seqr.utils.search.utils import backend_specific_call
from seqr.utils.search.elasticsearch.es_utils import validate_es_index_metadata_and_get_samples
from seqr.views.utils.airtable_utils import AirtableSession, ANVIL_REQUEST_TRACKING_TABLE
from seqr.views.utils.dataset_utils import match_and_update_search_samples, load_mapping_file
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, BASE_URL, ANVIL_UI_URL, \
    SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL


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
        updated_sample_data = updated_samples.values('sample_id', 'individual_id')
        _basic_notify_search_data_loaded(project, dataset_type, sample_type, inactivated_sample_guids, updated_sample_data)

    return inactivated_sample_guids, updated_family_guids, updated_samples


def _format_email(sample_summary, project_link, *args):
    return f'This is to notify you that {sample_summary} have been loaded in seqr project {project_link}'


def _basic_notify_search_data_loaded(project, dataset_type, sample_type, inactivated_sample_guids, updated_samples, format_email=_format_email):
    previous_loaded_individuals = set(Sample.objects.filter(guid__in=inactivated_sample_guids).values_list('individual_id', flat=True))
    new_sample_ids = [sample['sample_id'] for sample in updated_samples if sample['individual_id'] not in previous_loaded_individuals]

    url = f'{BASE_URL}project/{project.guid}/project_page'
    msg_dataset_type = '' if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS else f' {dataset_type}'
    num_new_samples = len(new_sample_ids)
    sample_summary = f'{num_new_samples} new {sample_type}{msg_dataset_type} samples'

    project_link = f'<a href={url}>{project.name}</a>'
    email = format_email(sample_summary, project_link, num_new_samples)

    send_project_notification(
        project,
        notification=f'Loaded {sample_summary}',
        email=email,
        subject='New data available in seqr',
    )

    return sample_summary, new_sample_ids, url


def notify_search_data_loaded(project, is_internal, dataset_type, sample_type, inactivated_sample_guids, updated_samples, num_samples):
    if is_internal:
        format_email = _format_email
    else:
        workspace_name = f'{project.workspace_namespace}/{project.workspace_name}'
        def format_email(sample_summary, project_link, num_new_samples):
            reload_summary = f' and {num_samples - num_new_samples} re-loaded samples' if num_samples > num_new_samples else ''
            return '\n'.join([
                f'We are following up on the request to load data from AnVIL on {project.created_date.date().strftime("%B %d, %Y")}.',
                f'We have loaded {sample_summary}{reload_summary} from the AnVIL workspace <a href={ANVIL_UI_URL}#workspaces/{workspace_name}>{workspace_name}</a> to the corresponding seqr project {project_link}.',
                'Let us know if you have any questions.',
            ])

    sample_summary, new_sample_ids, url = _basic_notify_search_data_loaded(
        project, dataset_type, sample_type, inactivated_sample_guids, updated_samples, format_email=format_email,
    )

    sample_id_list = f'\n```{", ".join(sorted(new_sample_ids))}```' if is_internal else ''
    summary_message = f'{sample_summary} are loaded in {url}{sample_id_list}'
    safe_post_to_slack(
        SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL if is_internal else SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL,
        summary_message)

    if not is_internal:
        AirtableSession(user=None, base=AirtableSession.ANVIL_BASE, no_auth=True).safe_patch_records(
            ANVIL_REQUEST_TRACKING_TABLE, max_records=1,
            record_or_filters={'Status': ['Loading', 'Loading Requested']},
            record_and_filters={'AnVIL Project URL': url},
            update={'Status': 'Available in Seqr'},
        )
