import json

from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, ANVIL_UI_URL, BASE_URL
from seqr.utils.communication_utils import send_html_email, safe_post_to_slack
from seqr.models import Individual, Sample, Family
from seqr.views.utils.dataset_utils import match_and_update_samples, load_mapping_file, \
    validate_index_metadata_and_get_elasticsearch_index_samples
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_samples
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, data_manager_required, \
    project_has_analyst_access, project_has_anvil, service_account_access


@data_manager_required
def add_variants_dataset_handler(request, project_guid):
    return add_variants_dataset_handler_base(request, project_guid)

def add_variants_dataset_handler_base(request, project_guid):
    """Create or update samples for the given variant dataset

    Args:
        request: Django request object
        project_guid (string): GUID of the project that should be updated

    HTTP POST
        Request body - should contain the following json structure:
        {
            'elasticsearchIndex': <String> (required)
            'ignoreExtraSamplesInCallset': <Boolean>
            'mappingFilePath':  <String>
        }

        Response body - will contain the following structure:

    """

    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    request_json = json.loads(request.body)

    required_fields = ['elasticsearchIndex', 'datasetType']
    if any(field not in request_json for field in required_fields):
        return create_json_response(
            {'errors': ['request must contain fields: {}'.format(', '.join(required_fields))]}, status=400)

    elasticsearch_index = request_json['elasticsearchIndex'].strip()
    dataset_type = request_json['datasetType']
    if dataset_type not in Sample.DATASET_TYPE_LOOKUP:
        return create_json_response({'errors': ['Invalid dataset type "{}"'.format(dataset_type)]}, status=400)

    try:
        sample_ids, sample_type = validate_index_metadata_and_get_elasticsearch_index_samples(
            elasticsearch_index, project=project, dataset_type=dataset_type)
        if not sample_ids:
            raise ValueError('No samples found in the index. Make sure the specified caller type is correct')

        sample_id_to_individual_id_mapping = load_mapping_file(
            request_json['mappingFilePath'], request.user) if request_json.get('mappingFilePath') else {}
    except ValueError as e:
        return create_json_response({'errors': [str(e)]}, status=400)

    ignore_extra_samples = request_json.get('ignoreExtraSamplesInCallset')
    try:
        samples, matched_individual_ids, activated_sample_guids, inactivated_sample_guids, updated_family_guids, _ = match_and_update_samples(
            projects=[project],
            user=request.user,
            sample_ids=sample_ids,
            elasticsearch_index=elasticsearch_index,
            sample_type=sample_type,
            dataset_type=dataset_type,
            sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
            raise_no_match_error=ignore_extra_samples,
            raise_unmatched_error_template=None if ignore_extra_samples else 'Matches not found for ES sample ids: {sample_ids}. Uploading a mapping file for these samples, or select the "Ignore extra samples in callset" checkbox to ignore.'
        )
    except ValueError as e:
        return create_json_response({'errors': [str(e)]}, status=400)

    updated_samples = Sample.objects.filter(guid__in=activated_sample_guids)

    if project_has_analyst_access(project):
        updated_individuals = {sample.individual_id for sample in updated_samples}
        previous_loaded_individuals = {
            sample.individual_id for sample in Sample.objects.filter(
                individual__in=updated_individuals, sample_type=sample_type, dataset_type=dataset_type,
            ).exclude(elasticsearch_index=elasticsearch_index)}
        previous_loaded_individuals.update(matched_individual_ids)
        new_sample_ids = [
            sample.sample_id for sample in updated_samples if sample.individual_id not in previous_loaded_individuals]
        safe_post_to_slack(
            SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
            """{num_sample} new {sample_type}{dataset_type} samples are loaded in {base_url}project/{guid}/project_page
            ```{samples}```
            """.format(
                num_sample=len(new_sample_ids),
                sample_type=sample_type,
                dataset_type='' if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS else ' {}'.format(dataset_type),
                base_url=BASE_URL,
                guid=project.guid,
                samples=', '.join(new_sample_ids)
            ))
    elif project_has_anvil(project):
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
                num_sample=len(samples),
            ),
            subject='New data available in seqr',
            to=sorted([user.email]),
        )

    response_json = _get_samples_json(updated_samples, inactivated_sample_guids, project_guid)
    response_json['familiesByGuid'] = {family_guid: {'analysisStatus': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}
                                       for family_guid in updated_family_guids}

    return create_json_response(response_json)


def _get_samples_json(updated_samples, inactivated_sample_guids, project_guid):
    updated_sample_json = get_json_for_samples(updated_samples, project_guid=project_guid)
    sample_response = {sample_guid: {'isActive': False} for sample_guid in inactivated_sample_guids}
    sample_response.update({s['sampleGuid']: s for s in updated_sample_json})
    response = {
        'samplesByGuid': sample_response
    }
    updated_individuals = {s['individualGuid'] for s in updated_sample_json}
    if updated_individuals:
        individuals = Individual.objects.filter(guid__in=updated_individuals).prefetch_related('sample_set')
        response['individualsByGuid'] = {
            ind.guid: {'sampleGuids': [s.guid for s in ind.sample_set.all()]} for ind in individuals
        }
    return response

# Service account access

@service_account_access
def sa_add_variants_dataset(request, project_guid):
    return add_variants_dataset_handler_base(request, project_guid)
    