import json

from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, ANVIL_UI_URL, BASE_URL, \
    SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL
from seqr.utils.communication_utils import send_html_email, safe_post_to_slack
from seqr.utils.search.add_data_utils import add_new_search_samples
from seqr.models import Individual, Family
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_samples
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, data_manager_required, \
    is_internal_anvil_project, project_has_anvil


@data_manager_required
def add_variants_dataset_handler(request, project_guid):
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

    is_internal = is_internal_anvil_project(project)
    has_anvil = project_has_anvil(project)
    summary_template = None
    if has_anvil:
        url = f'{BASE_URL}project/{project.guid}/project_page'
        summary_template = '{num_new_samples} new {sample_type}{dataset_type} samples are loaded in ' + url
        if is_internal:
            summary_template += '\n```{new_sample_id_list}```'

    try:
        num_sample, inactivated_sample_guids, updated_family_guids, updated_samples, summary_message = add_new_search_samples(
            request_json, project, request.user, summary_template=summary_template)
    except ValueError as e:
        return create_json_response({'errors': [str(e)]}, status=400)

    if summary_message:
        safe_post_to_slack(
            SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL if is_internal else SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL,
            summary_message)

    if has_anvil and not is_internal:
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
                num_sample=num_sample,
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
