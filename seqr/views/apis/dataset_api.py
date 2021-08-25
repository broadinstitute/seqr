import json
from collections import defaultdict

from django.db.models import prefetch_related_objects
from django.utils import timezone

from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, ANVIL_UI_URL, BASE_URL
from seqr.utils.communication_utils import send_html_email, safe_post_to_slack
from seqr.models import Individual, Sample, Family
from seqr.views.utils.dataset_utils import match_sample_ids_to_sample_records, \
    validate_index_metadata_and_get_elasticsearch_index_samples, load_mapping_file
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_samples
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, data_manager_required, \
    project_has_analyst_access, project_has_anvil


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

    loaded_date = timezone.now()
    matched_sample_id_to_sample_record, new_samples = match_sample_ids_to_sample_records(
        project=project,
        user=request.user,
        sample_ids=sample_ids,
        sample_type=sample_type,
        dataset_type=dataset_type,
        elasticsearch_index=elasticsearch_index,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        loaded_date=loaded_date,
    )

    unmatched_samples = set(sample_ids) - set(matched_sample_id_to_sample_record.keys())

    if request_json.get('ignoreExtraSamplesInCallset'):
        if len(matched_sample_id_to_sample_record) == 0:
            return create_json_response({'errors': [
                'None of the individuals or samples in the project matched the {} expected sample id(s)'.format(
                    len(sample_ids)
                )]}, status=400)
    elif len(unmatched_samples) > 0:
        return create_json_response({'errors': [
            'Matches not found for ES sample ids: {}. Uploading a mapping file for these samples, or select the "Ignore extra samples in callset" checkbox to ignore.'.format(
                ", ".join(unmatched_samples))
        ]}, status=400)

    prefetch_related_objects(list(matched_sample_id_to_sample_record.values()), 'individual__family')
    included_families = {sample.individual.family for sample in matched_sample_id_to_sample_record.values()}

    missing_individuals = Individual.objects.filter(
        family__in=included_families,
        sample__is_active=True,
        sample__dataset_type=dataset_type,
        sample__sample_type=sample_type,
    ).exclude(sample__in=matched_sample_id_to_sample_record.values()).select_related('family')
    missing_family_individuals = defaultdict(list)
    for individual in missing_individuals:
        missing_family_individuals[individual.family].append(individual)

    if missing_family_individuals:
        return create_json_response({'errors': [
            'The following families are included in the callset but are missing some family members: {}.'.format(
                ', '.join(sorted(
                    ['{} ({})'.format(family.family_id, ', '.join(sorted([i.individual_id for i in missing_indivs])))
                     for family, missing_indivs in missing_family_individuals.items()]
                )))]}, status=400)

    inactivate_sample_guids = _update_variant_samples(
        matched_sample_id_to_sample_record, request.user, elasticsearch_index, loaded_date, dataset_type, sample_type)

    family_guids_to_update = [
        family.guid for family in included_families if family.analysis_status == Family.ANALYSIS_STATUS_WAITING_FOR_DATA
    ]
    Family.bulk_update(
        request.user, {'analysis_status': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}, guid__in=family_guids_to_update)

    if project_has_analyst_access(project):
        safe_post_to_slack(
            SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
            """{num_sample} new samples are loaded in {base_url}project/{guid}/project_page
            ```{samples}```
            """.format(
                num_sample=len(new_samples),
                base_url=BASE_URL,
                guid=project.guid,
                samples=[sample.sample_id for sample in new_samples]
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
                num_sample=len(matched_sample_id_to_sample_record),
            ),
            subject='New data available in seqr',
            to=sorted([user.email]),
        )

    response_json = _get_samples_json(matched_sample_id_to_sample_record, inactivate_sample_guids, project_guid)
    response_json['familiesByGuid'] = {family_guid: {'analysisStatus': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}
                                       for family_guid in family_guids_to_update}

    return create_json_response(response_json)


def _update_variant_samples(matched_sample_id_to_sample_record, user, elasticsearch_index, loaded_date=None,
                            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS, sample_type=Sample.SAMPLE_TYPE_WES):
    if not loaded_date:
        loaded_date = timezone.now()
    updated_samples = [sample.id for sample in matched_sample_id_to_sample_record.values()]

    activated_sample_guids = Sample.bulk_update(user, {
        'elasticsearch_index': elasticsearch_index,
        'is_active': True,
        'loaded_date': loaded_date,
    }, id__in=updated_samples, is_active=False)

    matched_sample_id_to_sample_record.update({
        sample.sample_id: sample for sample in Sample.objects.filter(guid__in=activated_sample_guids)
    })

    inactivate_samples = Sample.objects.filter(
        individual_id__in={sample.individual_id for sample in matched_sample_id_to_sample_record.values()},
        is_active=True,
        dataset_type=dataset_type,
        sample_type=sample_type,
    ).exclude(id__in=updated_samples)

    inactivate_sample_guids = Sample.bulk_update(user, {'is_active': False}, queryset=inactivate_samples)

    return inactivate_sample_guids


def _get_samples_json(matched_sample_id_to_sample_record, inactivate_sample_guids, project_guid):
    updated_sample_json = get_json_for_samples(list(matched_sample_id_to_sample_record.values()), project_guid=project_guid)
    sample_response = {sample_guid: {'isActive': False} for sample_guid in inactivate_sample_guids}
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
