from collections import defaultdict, OrderedDict
from django.contrib.auth.models import User
from django.db.models import F
from typing import Callable

from reference_data.models import GENOME_VERSION_LOOKUP
from seqr.models import Sample, Individual, Project
from seqr.utils.communication_utils import send_project_notification
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.search.utils import backend_specific_call
from seqr.utils.search.elasticsearch.es_utils import validate_es_index_metadata_and_get_samples
from seqr.views.utils.airtable_utils import AirtableSession, ANVIL_REQUEST_TRACKING_TABLE
from seqr.views.utils.dataset_utils import match_and_update_search_samples, load_mapping_file
from seqr.views.utils.export_utils import write_multiple_files
from seqr.views.utils.pedigree_info_utils import JsonConstants
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, BASE_URL, ANVIL_UI_URL, \
    SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL

logger = SeqrLogger(__name__)


def _no_es_backend_error(*args, **kwargs):
    raise ValueError('Adding samples is disabled without the elasticsearch backend')


def add_new_es_search_samples(request_json, project, user, notify=False, expected_families=None):
    dataset_type = request_json.get('datasetType')
    if dataset_type not in Sample.DATASET_TYPE_LOOKUP:
        raise ValueError(f'Invalid dataset type "{dataset_type}"')

    sample_ids, sample_type, sample_data = backend_specific_call(
        validate_es_index_metadata_and_get_samples,
        _no_es_backend_error,
        _no_es_backend_error,
    )(request_json, project)
    if not sample_ids:
        raise ValueError('No samples found. Make sure the specified caller type is correct')

    sample_id_to_individual_id_mapping = load_mapping_file(
        request_json['mappingFilePath'], user) if request_json.get('mappingFilePath') else {}
    ignore_extra_samples = request_json.get('ignoreExtraSamplesInCallset')
    sample_project_tuples = [(sample_id, project.name) for sample_id in sample_ids]
    new_samples, updated_samples, inactivated_sample_guids, updated_family_guids = match_and_update_search_samples(
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
        _basic_notify_search_data_loaded(project, dataset_type, sample_type, new_samples.values_list('sample_id'))

    return inactivated_sample_guids, updated_family_guids, updated_samples


def _basic_notify_search_data_loaded(project, dataset_type, sample_type, new_samples, email_template=None, slack_channel=None, include_slack_detail=False):
    msg_dataset_type = '' if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS else f' {dataset_type}'
    num_new_samples = len(new_samples)
    sample_summary = f'{num_new_samples} new {sample_type}{msg_dataset_type} samples'

    return send_project_notification(
        project,
        notification=sample_summary,
        email_template=email_template,
        subject='New data available in seqr',
        slack_channel=slack_channel,
        slack_detail=', '.join(sorted(new_samples)) if include_slack_detail else None,
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

    _basic_notify_search_data_loaded(
        project, dataset_type, sample_type, new_samples, email_template=email_template,
        slack_channel=SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL if is_internal else SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL,
        include_slack_detail=is_internal,
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

def format_loading_pipeline_variables(
    projects: list[Project], genome_version: str, dataset_type: str, sample_type: str = None, **kwargs
):
    variables = {
        'projects_to_run': sorted([p.guid for p in projects]) if projects else None,
        'dataset_type': _dag_dataset_type(sample_type, dataset_type),
        'reference_genome': GENOME_VERSION_LOOKUP[genome_version],
        **kwargs
    }
    if sample_type:
        variables['sample_type'] = sample_type
    return variables

def prepare_data_loading_request(projects: list[Project], individual_ids: list[int], sample_type: str, dataset_type: str, genome_version: str,
                                 data_path: str, user: User, pedigree_dir: str,  raise_pedigree_error: bool = False,
                                 skip_validation: bool = False, skip_check_sex_and_relatedness: bool = False, vcf_sample_id_map=None):
    variables = format_loading_pipeline_variables(
        projects,
        genome_version,
        dataset_type,
        sample_type,
        callset_path=data_path,
    )
    if skip_validation:
        variables['skip_validation'] = True
    if skip_check_sex_and_relatedness:
        variables['skip_check_sex_and_relatedness'] = True
    file_path = _get_pedigree_path(pedigree_dir, genome_version, sample_type, dataset_type)
    _upload_data_loading_files(individual_ids, vcf_sample_id_map or {}, user, file_path, raise_pedigree_error)
    return variables, file_path


def _dag_dataset_type(sample_type: str, dataset_type: str):
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


def _get_pedigree_path(pedigree_dir: str, genome_version: str, sample_type: str, dataset_type: str):
    dag_dataset_type = _dag_dataset_type(sample_type, dataset_type)
    return f'{pedigree_dir}/{GENOME_VERSION_LOOKUP[genome_version]}/{dag_dataset_type}/pedigrees/{sample_type}'


def get_loading_samples_validator(vcf_samples: list[str], loaded_individual_ids: list[int], sample_source: str,
                                  missing_family_samples_error: str, loaded_sample_types: list[str] = None,
                                  fetch_missing_loaded_samples: Callable = None, fetch_missing_vcf_samples: Callable = None) -> Callable:

    def validate_expected_samples(record_family_ids, previous_loaded_individuals, sample_type):
        errors = []

        nonlocal loaded_sample_types
        if loaded_sample_types is not None:
            if sample_type:
                loaded_sample_types.append(sample_type)
            else:
                errors.append('New data cannot be added to this project until the previously requested data is loaded')

        families = set(record_family_ids.values())
        missing_samples_by_family = defaultdict(set)
        expected_sample_set = record_family_ids if fetch_missing_loaded_samples else vcf_samples
        for loaded_individual in previous_loaded_individuals:
            individual_id = loaded_individual[JsonConstants.INDIVIDUAL_ID_COLUMN]
            family_id = loaded_individual[JsonConstants.FAMILY_ID_COLUMN]
            if family_id in families and individual_id not in expected_sample_set:
                missing_samples_by_family[family_id].add(individual_id)

        loading_samples = set(record_family_ids.keys())
        if missing_samples_by_family and fetch_missing_loaded_samples:
            try:
                additional_loaded_samples = fetch_missing_loaded_samples()
                for missing_samples in missing_samples_by_family.values():
                    loading_samples.update(missing_samples.intersection(additional_loaded_samples))
                    missing_samples -= additional_loaded_samples
                missing_samples_by_family = {
                    family_id: samples for family_id, samples in missing_samples_by_family.items() if samples
                }
            except ValueError as e:
                errors.append(str(e))

        if missing_samples_by_family:
            missing_family_sample_messages = [
                f'Family {family_id}: {", ".join(sorted(individual_ids))}'
                for family_id, individual_ids in missing_samples_by_family.items()
            ]
            errors.append(
                missing_family_samples_error + '\n'.join(sorted(missing_family_sample_messages))
            )

        missing_vcf_samples = [] if vcf_samples is None else set(loading_samples - set(vcf_samples))
        if missing_vcf_samples and fetch_missing_vcf_samples:
            try:
                additional_vcf_samples = fetch_missing_vcf_samples(missing_vcf_samples)
                missing_vcf_samples -= set(additional_vcf_samples)
            except ValueError as e:
                errors.append(str(e))
        if missing_vcf_samples:
            errors.insert(
                0, f'The following samples are included in {sample_source} but are missing from the VCF: {", ".join(sorted(missing_vcf_samples))}',
            )

        nonlocal loaded_individual_ids
        loaded_individual_ids += [
            i['individual_id'] for i in previous_loaded_individuals if i[JsonConstants.FAMILY_ID_COLUMN] in families
        ]

        return errors

    return validate_expected_samples
