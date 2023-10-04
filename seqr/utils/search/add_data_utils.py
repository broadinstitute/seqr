from seqr.models import Sample
from seqr.utils.communication_utils import send_html_email, safe_post_to_slack
from seqr.utils.search.utils import backend_specific_call
from seqr.utils.search.elasticsearch.es_utils import validate_es_index_metadata_and_get_samples
from seqr.views.utils.dataset_utils import match_and_update_search_samples, load_mapping_file
from seqr.views.utils.permissions_utils import is_internal_anvil_project, project_has_anvil
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
        num_samples = len(sample_ids) - num_skipped
        notify_search_data_loaded(project, dataset_type, sample_type, inactivated_sample_guids, updated_samples, num_samples)

    return inactivated_sample_guids, updated_family_guids, updated_samples


def notify_search_data_loaded(project, dataset_type, sample_type, inactivated_sample_guids, updated_samples, num_samples):
    if not project_has_anvil(project):
        return
    is_internal = is_internal_anvil_project(project)

    previous_loaded_individuals = set(Sample.objects.filter(guid__in=inactivated_sample_guids).values_list('individual_id', flat=True))
    new_sample_ids = [sample.sample_id for sample in updated_samples if sample.individual_id not in previous_loaded_individuals]

    url = f'{BASE_URL}project/{project.guid}/project_page'
    msg_dataset_type = '' if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS else f' {dataset_type}'
    sample_id_list = f'\n```{", ".join(sorted(new_sample_ids))}```' if is_internal else ''
    summary_message = f'{len(new_sample_ids)} new {sample_type}{msg_dataset_type} samples are loaded in {url}{sample_id_list}'

    safe_post_to_slack(
        SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL if is_internal else SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL,
        summary_message)

    if is_internal:
        return

    user = project.created_by
    send_html_email("""Hi {user},
We are following up on your request to load data from AnVIL on {date}.
We have loaded {num_sample} samples from the AnVIL workspace <a href={anvil_url}#workspaces/{namespace}/{name}>{namespace}/{name}</a> to the corresponding seqr project <a href={base_url}project/{guid}/project_page>{project_name}</a>. Let us know if you have any questions.
- The seqr team
""".format(
        user=user.get_full_name() or user.email,
        date=project.created_date.date().strftime('%B %d, %Y'),
        anvil_url=ANVIL_UI_URL,
        namespace=project.workspace_namespace,
        name=project.workspace_name,
        base_url=BASE_URL,
        guid=project.guid,
        project_name=project.name,
        num_sample=num_samples,
    ),
        subject='New data available in seqr',
        to=sorted([user.email]),
    )
