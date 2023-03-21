import elasticsearch_dsl
from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import prefetch_related_objects, Q
from django.utils import timezone
from tqdm import tqdm
import random

from seqr.models import Sample, Individual, Family, Project, RnaSeqOutlier, RnaSeqTpm
from seqr.utils.communication_utils import safe_post_to_slack
from seqr.utils.elasticsearch.utils import get_es_client, get_index_metadata
from seqr.utils.file_utils import file_iter
from seqr.utils.logging_utils import log_model_bulk_update, SeqrLogger
from seqr.views.utils.file_utils import parse_file
from seqr.views.utils.permissions_utils import get_internal_projects
from seqr.views.utils.json_utils import _to_snake_case, _to_camel_case
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, BASE_URL

logger = SeqrLogger(__name__)

SAMPLE_FIELDS_LIST = ['samples', 'samples_num_alt_1']
VCF_FILE_EXTENSIONS = ('.vcf', '.vcf.gz', '.vcf.bgz')
#  support .bgz instead of requiring .vcf.bgz due to issues with DSP delivery of large callsets
DATASET_FILE_EXTENSIONS = VCF_FILE_EXTENSIONS[:-1] + ('.bgz', '.bed', '.mt')


def validate_index_metadata_and_get_elasticsearch_index_samples(elasticsearch_index, **kwargs):
    es_client = get_es_client()

    all_index_metadata = get_index_metadata(elasticsearch_index, es_client, include_fields=True)
    if elasticsearch_index in all_index_metadata:
        index_metadata = all_index_metadata.get(elasticsearch_index)
        validate_index_metadata(index_metadata, elasticsearch_index, **kwargs)
        sample_field = _get_samples_field(index_metadata)
        sample_type = index_metadata['sampleType']
    else:
        # Aliases return the mapping for all indices in the alias
        metadatas = list(all_index_metadata.values())
        sample_field = _get_samples_field(metadatas[0])
        sample_type = metadatas[0]['sampleType']
        for metadata in metadatas[1:]:
            validate_index_metadata(metadata, elasticsearch_index, **kwargs)
            if sample_field != _get_samples_field(metadata):
                raise ValueError('Found mismatched sample fields for indices in alias')
            if sample_type != metadata['sampleType']:
                raise ValueError('Found mismatched sample types for indices in alias')

    s = elasticsearch_dsl.Search(using=es_client, index=elasticsearch_index)
    s = s.params(size=0)
    s.aggs.bucket('sample_ids', elasticsearch_dsl.A('terms', field=sample_field, size=10000))
    response = s.execute()
    return [agg['key'] for agg in response.aggregations.sample_ids.buckets], sample_type


def _get_samples_field(index_metadata):
    return next((field for field in SAMPLE_FIELDS_LIST if field in index_metadata['fields'].keys()))


def validate_index_metadata(index_metadata, elasticsearch_index, project=None, genome_version=None,
                            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS):
    metadata_fields = ['genomeVersion', 'sampleType', 'sourceFilePath']
    if any(field not in (index_metadata or {}) for field in metadata_fields):
        raise ValueError("Index metadata must contain fields: {}".format(', '.join(metadata_fields)))

    sample_type = index_metadata['sampleType']
    if sample_type not in {choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES}:
        raise ValueError("Sample type not supported: {}".format(sample_type))

    if index_metadata['genomeVersion'] != (genome_version or project.genome_version):
        raise ValueError('Index "{0}" has genome version {1} but this project uses version {2}'.format(
            elasticsearch_index, index_metadata['genomeVersion'], project.genome_version
        ))

    dataset_path = index_metadata['sourceFilePath']
    if not dataset_path.endswith(DATASET_FILE_EXTENSIONS):
        raise ValueError("Variant call dataset path must end with {}".format(' or '.join(DATASET_FILE_EXTENSIONS)))

    if index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS) != dataset_type:
        raise ValueError('Index "{0}" has dataset type {1} but expects {2}'.format(
            elasticsearch_index, index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS), dataset_type
        ))


def load_mapping_file(mapping_file_path, user):
    file_content = parse_file(mapping_file_path, file_iter(mapping_file_path, user=user))
    return load_mapping_file_content(file_content)


def load_mapping_file_content(file_content):
    id_mapping = {}
    for line in file_content:
        if len(line) != 2:
            raise ValueError("Must contain 2 columns: " + ', '.join(line))
        id_mapping[line[0]] = line[1]
    return id_mapping


def _get_individual_sample_lookup(individuals):
    return {(i.individual_id, None): i for i in individuals}


def _get_mapped_individual_lookup_key(sample_id_to_individual_id_mapping):
    sample_id_to_individual_id_mapping = sample_id_to_individual_id_mapping or {}

    def _get_mapped_id(sample_id):
        return sample_id_to_individual_id_mapping.get(sample_id, sample_id)
    return _get_mapped_id


def _find_or_create_missing_sample_records(
        samples,
        projects,
        user,
        sample_project_tuples,
        get_individual_sample_key,
        remaining_sample_keys,
        raise_no_match_error=False,
        raise_unmatched_error_template=None,
        create_active=False,
        get_individual_sample_lookup=_get_individual_sample_lookup,
        **kwargs
):
    samples = list(samples)
    remaining_sample_ids = set()
    matched_individual_ids = {sample.individual_id for sample in samples}
    if len(remaining_sample_keys) > 0:
        remaining_individuals_dict = get_individual_sample_lookup(
            Individual.objects.filter(family__project__in=projects).exclude(id__in=matched_individual_ids)
        )

        # find Individual records with exactly-matching individual_ids
        sample_id_to_individual_record = {}
        for sample_key in remaining_sample_keys:
            individual_key = (get_individual_sample_key(sample_key[0]), sample_key[1])
            if individual_key not in remaining_individuals_dict:
                continue
            sample_id_to_individual_record[sample_key] = remaining_individuals_dict[individual_key]
            del remaining_individuals_dict[individual_key]

        logger.debug(str(len(sample_id_to_individual_record)) + " matched individual ids", user)

        remaining_sample_keys -= set(sample_id_to_individual_record.keys())
        if raise_no_match_error and len(remaining_sample_keys) == len(sample_project_tuples):
            raise ValueError(
                'None of the individuals or samples in the project matched the {} expected sample id(s)'.format(
                    len(sample_project_tuples)
                ))
        remaining_sample_ids = {sample_id for sample_id, _ in remaining_sample_keys}
        if raise_unmatched_error_template and remaining_sample_ids:
            raise ValueError(raise_unmatched_error_template.format(sample_ids=(', '.join(sorted(remaining_sample_ids)))))

        # create new Sample records for Individual records that matches
        new_samples = [
            Sample(
                guid='S{}_{}'.format(random.randint(10**9, 10**10), sample_id)[:Sample.MAX_GUID_SIZE], # nosec
                sample_id=sample_id,
                individual=individual,
                created_date=timezone.now(),
                is_active=create_active,
                **kwargs
            ) for (sample_id, _), individual in sample_id_to_individual_record.items()]
        samples += list(Sample.bulk_create(user, new_samples))
        log_model_bulk_update(logger, new_samples, user, 'create')

    return samples, matched_individual_ids, remaining_sample_ids


def _validate_samples_families(samples, included_families, sample_type, dataset_type, expected_families=None):
    missing_individuals = Individual.objects.filter(
        family__in=included_families,
        sample__is_active=True,
        sample__dataset_type=dataset_type,
        sample__sample_type=sample_type,
    ).exclude(sample__in=samples).select_related('family')
    missing_family_individuals = defaultdict(list)
    for individual in missing_individuals:
        missing_family_individuals[individual.family].append(individual)

    if missing_family_individuals:
        raise ValueError(
            'The following families are included in the callset but are missing some family members: {}.'.format(
                ', '.join(sorted(
                    ['{} ({})'.format(family.family_id, ', '.join(sorted([i.individual_id for i in missing_indivs])))
                     for family, missing_indivs in missing_family_individuals.items()]
                ))))

    if expected_families:
        missing_families = expected_families - included_families
        if missing_families:
            raise ValueError(
                'The following families have saved variants but are missing from the callset: {}.'.format(
                    ', '.join([f.family_id for f in missing_families])
                ))


def _update_variant_samples(samples, user, elasticsearch_index, loaded_date, dataset_type, sample_type):
    updated_samples = [sample.id for sample in samples]

    activated_sample_guids = Sample.bulk_update(user, {
        'elasticsearch_index': elasticsearch_index,
        'is_active': True,
        'loaded_date': loaded_date,
    }, id__in=updated_samples, is_active=False)

    inactivate_sample_guids = []
    if elasticsearch_index:
        inactivate_samples = Sample.objects.filter(
            individual_id__in={sample.individual_id for sample in samples},
            is_active=True,
            dataset_type=dataset_type,
            sample_type=sample_type,
        ).exclude(id__in=updated_samples)

        inactivate_sample_guids = Sample.bulk_update(user, {'is_active': False}, queryset=inactivate_samples)

    return activated_sample_guids, inactivate_sample_guids


def match_and_update_search_samples(
        project, user, sample_ids, elasticsearch_index, sample_type, dataset_type,
        sample_id_to_individual_id_mapping, raise_unmatched_error_template, expected_families=None,
):
    samples = Sample.objects.select_related('individual').filter(
        individual__family__project=project,
        sample_type=sample_type,
        dataset_type=dataset_type,
        sample_id__in=sample_ids,
        elasticsearch_index=elasticsearch_index,
    )
    loaded_date = timezone.now()
    get_individual_sample_key = _get_mapped_individual_lookup_key(sample_id_to_individual_id_mapping)
    sample_project_tuples = [(sample_id, None) for sample_id in sample_ids]
    samples, matched_individual_ids, _ = _find_or_create_missing_sample_records(
        samples=samples,
        projects=[project],
        user=user,
        sample_project_tuples=sample_project_tuples,
        get_individual_sample_key=get_individual_sample_key,
        remaining_sample_keys=set(sample_project_tuples) - {(sample.sample_id, None) for sample in samples},
        elasticsearch_index=elasticsearch_index,
        sample_type=sample_type,
        dataset_type=dataset_type,
        loaded_date=loaded_date,
        raise_no_match_error=not raise_unmatched_error_template,
        raise_unmatched_error_template=raise_unmatched_error_template,
    )

    prefetch_related_objects(samples, 'individual__family')
    included_families = {sample.individual.family for sample in samples}
    _validate_samples_families(samples, included_families, sample_type, dataset_type, expected_families=expected_families)

    activated_sample_guids, inactivated_sample_guids = _update_variant_samples(
        samples, user, elasticsearch_index, loaded_date, dataset_type, sample_type)

    family_guids_to_update = [
        family.guid for family in included_families if family.analysis_status == Family.ANALYSIS_STATUS_WAITING_FOR_DATA
    ]
    Family.bulk_update(
        user, {'analysis_status': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}, guid__in=family_guids_to_update)

    # refresh sample models to get updated values
    samples = Sample.objects.filter(id__in=[s.id for s in samples])

    return samples, matched_individual_ids, activated_sample_guids, inactivated_sample_guids, family_guids_to_update


def _match_and_update_rna_samples(
    projects, user, sample_project_tuples, data_source, sample_id_to_individual_id_mapping, raise_unmatched_error_template,
):
    samples = Sample.objects.select_related('individual__family__project').filter(
        individual__family__project__in=projects,
        sample_type=Sample.SAMPLE_TYPE_RNA,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_id__in={sample_id for sample_id, _ in sample_project_tuples},
    )

    samples = [s for s in samples if (s.sample_id, s.individual.family.project.name) in sample_project_tuples]

    get_individual_sample_key = _get_mapped_individual_lookup_key(sample_id_to_individual_id_mapping)
    samples, _, remaining_sample_ids = _find_or_create_missing_sample_records(
        samples=samples,
        projects=projects,
        user=user,
        sample_project_tuples=sample_project_tuples,
        get_individual_sample_key=get_individual_sample_key,
        remaining_sample_keys=set(sample_project_tuples) - {
            (s.sample_id, s.individual.family.project.name) for s in samples},
        data_source=data_source,
        sample_type=Sample.SAMPLE_TYPE_RNA,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        loaded_date=timezone.now(),
        raise_no_match_error=False,
        raise_unmatched_error_template=raise_unmatched_error_template,
        create_active=True,
        get_individual_sample_lookup=lambda inds: {(i.individual_id, i.family.project.name):
                                                       i for i in inds.select_related('family__project')},
    )

    return samples, remaining_sample_ids

def _parse_tsv_row(row):
    return [s.strip().strip('"') for s in row.rstrip('\n').split('\t')]

PROJECT_COL = 'project'
RNA_OUTLIER_COLUMNS = {'geneID': 'gene_id', 'pValue': 'p_value', 'padjust': 'p_adjust', 'zScore': 'z_score',
                       PROJECT_COL: PROJECT_COL}

SAMPLE_ID_COL = 'sample_id'
GENE_ID_COL = 'gene_id'
TPM_COL = 'TPM'
TISSUE_COL = 'tissue'
INDIV_ID_COL = 'individual_id'
TPM_HEADER_COLS = [SAMPLE_ID_COL, PROJECT_COL, GENE_ID_COL, TISSUE_COL, TPM_COL]

TISSUE_TYPE_MAP = {
    'whole_blood': 'WB',
    'fibroblasts': 'F',
    'muscle': 'M',
    'lymphocytes': 'L',
}

REVERSE_TISSUE_TYPE = {v: k for k, v in TISSUE_TYPE_MAP.items()}

def _parse_outlier_row(row, **kwargs):
    yield row['sampleID'], {mapped_key: row[key] for key, mapped_key in RNA_OUTLIER_COLUMNS.items()}

def _parse_tpm_row(row, sample_id_to_tissue_type=None):
    sample_id = row[SAMPLE_ID_COL]
    if row[TPM_COL] != '0.0' and not sample_id.startswith('GTEX'):
        prev_tissue = sample_id_to_tissue_type.get(sample_id)
        tissue = row[TISSUE_COL]
        if not tissue:
            raise ValueError(f'Sample {sample_id} has no tissue type')
        if prev_tissue and prev_tissue != tissue:
            raise ValueError(f'Mismatched tissue types for sample {sample_id}: {prev_tissue}, {tissue}')
        sample_id_to_tissue_type[sample_id] = tissue

        parsed = {GENE_ID_COL: row[GENE_ID_COL], 'tpm': row[TPM_COL], PROJECT_COL: row[PROJECT_COL]}
        if INDIV_ID_COL in row:
            parsed[INDIV_ID_COL] = row[INDIV_ID_COL]

        yield sample_id, parsed

def _check_invalid_tissues(samples, sample_id_to_tissue_type, warnings):
    invalid_tissues = {}
    for sample in samples:
        tissue_type = TISSUE_TYPE_MAP[sample_id_to_tissue_type[sample.sample_id]]
        if not sample.tissue_type:
            sample.tissue_type = tissue_type
            sample.save()
        elif sample.tissue_type != tissue_type:
            invalid_tissues[sample] = tissue_type

    if invalid_tissues:
        mismatch = ', '.join([
            f'{sample.sample_id} ({REVERSE_TISSUE_TYPE[expected_tissue]} to {REVERSE_TISSUE_TYPE[sample.tissue_type]})'
            for sample, expected_tissue in invalid_tissues.items()])
        message = f'Skipped data loading for the following {len(invalid_tissues)} samples due to mismatched tissue type: {mismatch}'
        warnings.append(message)

    return [sample for sample in samples if sample not in invalid_tissues]

def load_rna_seq_outlier(file_path, user=None, mapping_file=None, ignore_extra_samples=False):
    expected_columns = ['sampleID'] + list(RNA_OUTLIER_COLUMNS.keys())
    return _load_rna_seq(
        RnaSeqOutlier, file_path, user, mapping_file, ignore_extra_samples, _parse_outlier_row, expected_columns,
    )

def load_rna_seq_tpm(file_path, user=None, mapping_file=None, ignore_extra_samples=False):
    sample_id_to_tissue_type = {}
    return _load_rna_seq(
        RnaSeqTpm, file_path, user, mapping_file, ignore_extra_samples, _parse_tpm_row, TPM_HEADER_COLS,
        sample_id_to_tissue_type=sample_id_to_tissue_type, validate_samples=_check_invalid_tissues,
    )

def _load_rna_seq(model_cls, file_path, user, mapping_file, ignore_extra_samples, parse_row, expected_columns,
                  sample_id_to_tissue_type=None, validate_samples=None):
    sample_id_to_individual_id_mapping = {}
    if mapping_file:
        sample_id_to_individual_id_mapping = load_mapping_file_content(mapping_file)

    samples_by_id = defaultdict(dict)
    f = file_iter(file_path)
    header = _parse_tsv_row(next(f))
    missing_cols = set(expected_columns) - set(header)
    if missing_cols:
        raise ValueError(f'Invalid file: missing column(s) {", ".join(sorted(missing_cols))}')

    for line in tqdm(f, unit=' rows'):
        row = dict(zip(header, _parse_tsv_row(line)))
        for sample_id, row_dict in parse_row(row, sample_id_to_tissue_type=sample_id_to_tissue_type):
            gene_id = row_dict['gene_id']
            project = row_dict.pop(PROJECT_COL)
            existing_data = samples_by_id[(sample_id, project)].get(gene_id)
            if existing_data and existing_data != row_dict:
                raise ValueError(
                    f'Error in {sample_id} data for {gene_id}: mismatched entries {existing_data} and {row_dict}')

            indiv_id = row_dict.pop(INDIV_ID_COL, None)
            if indiv_id and sample_id not in sample_id_to_individual_id_mapping:
                sample_id_to_individual_id_mapping[sample_id] = indiv_id

            samples_by_id[(sample_id, project)][gene_id] = row_dict

    message = f'Parsed {len(samples_by_id)} RNA-seq samples'
    info = [message]
    logger.info(message, user)

    data_source = file_path.split('/')[-1].split('_-_')[-1]
    samples, remaining_sample_ids = _match_and_update_rna_samples(
        projects=get_internal_projects(),
        user=user,
        sample_project_tuples=samples_by_id.keys(),
        data_source=data_source,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        raise_unmatched_error_template=None if ignore_extra_samples else 'Unable to find matches for the following samples: {sample_ids}'
    )

    warnings = []
    if validate_samples:
        samples = validate_samples(samples, sample_id_to_tissue_type, warnings)

    # Delete old data
    to_delete = model_cls.objects.filter(sample__in=samples).exclude(sample__data_source=data_source)
    prev_loaded_individual_ids = set(to_delete.values_list('sample__individual_id', flat=True))
    if to_delete:
        model_cls.bulk_delete(user, to_delete)

    loaded_sample_ids = set(model_cls.objects.filter(sample__in=samples).values_list('sample_id', flat=True).distinct())
    samples = Sample.objects.select_related('individual__family__project').filter(id__in={s.id for s in samples} - loaded_sample_ids)
    samples_to_load = {
        sample: samples_by_id[(sample.sample_id, sample.individual.family.project.name)] for sample in samples
    }

    sample_projects = Project.objects.filter(family__individual__sample__in=samples_to_load.keys()).values(
        'guid', 'name', new_sample_ids=ArrayAgg(
            'family__individual__sample__sample_id', distinct=True, ordering='family__individual__sample__sample_id',
            filter=~Q(family__individual__id__in=prev_loaded_individual_ids) if prev_loaded_individual_ids else None
        ))
    project_names = ', '.join(sorted([project['name'] for project in sample_projects]))
    message = f'Attempted data loading for {len(samples_to_load)} RNA-seq samples in the following {len(sample_projects)} projects: {project_names}'
    info.append(message)
    logger.info(message, user)

    _notify_rna_loading(model_cls, sample_projects)

    if remaining_sample_ids:
        skipped_samples = ', '.join(sorted(remaining_sample_ids))
        message = f'Skipped loading for the following {len(remaining_sample_ids)} unmatched samples: {skipped_samples}'
        warnings.append(message)
    if loaded_sample_ids:
        message = f'Skipped loading for {len(loaded_sample_ids)} samples already loaded from this file'
        warnings.append(message)

    for warning in warnings:
        logger.warning(warning, user)

    return samples_to_load, info, warnings


def _notify_rna_loading(model_cls, sample_projects):
    data_type = 'Outlier' if model_cls == RnaSeqOutlier else 'Expression'
    for project_agg in sample_projects:
        new_ids = project_agg["new_sample_ids"]
        project_link = f'<{BASE_URL}project/{project_agg["guid"]}/project_page|{project_agg["name"]}>'
        safe_post_to_slack(
            SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
            f'{len(new_ids)} new RNA {data_type} samples are loaded in {project_link}\n```{", ".join(new_ids)}```'
        )


PHENOTYPE_PRIORITIZATION_HEADER = ['tool', 'project', 'sampleId', 'rank', 'geneId', 'diseaseId', 'diseaseName']
PHENOTYPE_PRIORITIZATION_REQUIRED_HEADER = PHENOTYPE_PRIORITIZATION_HEADER + ['scoreName1', 'score1']
MAX_SCORES = 16


def _parse_phenotype_pri_row(row):
    record = {_to_snake_case(key): row.get(key) for key in PHENOTYPE_PRIORITIZATION_HEADER}

    scores = {}
    for i in range(1, MAX_SCORES):
        score_name = row.get(f'scoreName{i}')
        if not score_name:
            break
        # We have both camel case and snake case in the score field names, so convert them to snake case first (those
        # in snake case kept unchanged), then to camel case.
        score = row[f'score{i}']
        if score:
            scores[_to_camel_case(_to_snake_case(score_name))] = float(score)
    record['scores'] = scores

    yield record


def load_phenotype_prioritization_data_file(file_path):
    data_by_project_sample_id = defaultdict(lambda: defaultdict(list))
    f = file_iter(file_path)
    header = _parse_tsv_row(next(f))
    missing_cols = [col for col in PHENOTYPE_PRIORITIZATION_REQUIRED_HEADER if col not in header]
    if missing_cols:
        raise ValueError(f'Invalid file: missing column(s) {", ".join(missing_cols)}')

    tool = None
    for line in tqdm(f, unit=' rows'):
        row = dict(zip(header, _parse_tsv_row(line)))
        for row_dict in _parse_phenotype_pri_row(row):
            sample_id = row_dict.pop('sample_id', None)
            project = row_dict.pop('project', None)
            if not sample_id or not project:
                raise ValueError('Both sample ID and project fields are required.')
            data_by_project_sample_id[project][sample_id].append(row_dict)
            if not tool:
                tool = row_dict['tool']
            elif tool != row_dict['tool']:
                raise ValueError(f'Multiple tools found {tool} and {row_dict["tool"]}. Only one in a file is supported.')

    return tool, data_by_project_sample_id
