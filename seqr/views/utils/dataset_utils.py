import elasticsearch_dsl
from collections import defaultdict
from django.db.models import prefetch_related_objects
from django.utils import timezone
from tqdm import tqdm
import random

from seqr.models import Sample, Individual, Family, Project, RnaSeqOutlier, RnaSeqTpm
from seqr.utils.elasticsearch.utils import get_es_client, get_index_metadata
from seqr.utils.file_utils import file_iter
from seqr.utils.logging_utils import log_model_bulk_update, SeqrLogger
from seqr.views.utils.file_utils import parse_file
from settings import ANALYST_PROJECT_CATEGORY

logger = SeqrLogger(__name__)

SAMPLE_FIELDS_LIST = ['samples', 'samples_num_alt_1']
VCF_FILE_EXTENSIONS = ('.vcf', '.vcf.gz', '.vcf.bgz')
#  support .bgz instead of requiring .vcf.bgz due to issues with DSP delivery of large callsets
DATASET_FILE_EXTENSIONS = VCF_FILE_EXTENSIONS[:-1] + ('.bgz', '.bed')


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

def match_sample_ids_to_sample_records(
        projects,
        user,
        sample_ids,
        elasticsearch_index,
        sample_type,
        data_source=None,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_id_to_individual_id_mapping=None,
        loaded_date=None,
        raise_no_match_error=False,
        raise_unmatched_error_template=None,
):
    """Goes through the given list of sample_ids and finds existing Sample records of the given
    sample_type and dataset_type with ids from the list. For sample_ids that aren't found to have existing Sample
    records, it looks for Individual records that have an individual_id that exactly equals one of the sample_ids in
    the list or is contained in the optional sample_id_to_individual_id_mapping and creates new Sample records for these

    Args:
        projects (object array): List of Django ORM project models
        user (object): Django ORM User model
        sample_ids (list): a list of sample ids for which to find matching Sample records
        sample_type (string): one of the Sample.SAMPLE_TYPE_* constants
        dataset_type (string): one of the Sample.DATASET_TYPE_* constants
        elasticsearch_index (string): an optional string specifying the index where the dataset is loaded
        data_source (string): an optional string specifying the a non-elasticsearch source for the dataset
        sample_id_to_individual_id_mapping (object): Mapping between sample ids and their corresponding individual ids
        loaded_date (object): datetime object
        raise_no_match_error (bool): whether to raise an exception if no sample matches are found
        raise_unmatched_error_template (string): optional template to use to raise an exception if samples are unmatched, will not raise if not provided

    Returns:
        tuple:
            [0] array: matching Sample records (including any newly-created ones)
            [1] array: Family records with matched samples
            [2] array: ids of Individuals with exact-matching existing samples
    """

    samples = _find_matching_sample_records(
        projects, sample_ids, sample_type, dataset_type, elasticsearch_index,
    )
    logger.debug(str(len(samples)) + " exact sample record matches", user)

    remaining_sample_ids = set(sample_ids) - {sample.sample_id for sample in samples}
    matched_individual_ids = {sample.individual_id for sample in samples}
    if len(remaining_sample_ids) > 0:
        remaining_individuals_dict = {
            i.individual_id: i for i in
            Individual.objects.filter(family__project__in=projects).exclude(id__in=matched_individual_ids)
        }

        # find Individual records with exactly-matching individual_ids
        sample_id_to_individual_record = {}
        for sample_id in remaining_sample_ids:
            individual_id = sample_id
            if sample_id_to_individual_id_mapping and sample_id in sample_id_to_individual_id_mapping:
                individual_id = sample_id_to_individual_id_mapping[sample_id]

            if individual_id not in remaining_individuals_dict:
                continue
            sample_id_to_individual_record[sample_id] = remaining_individuals_dict[individual_id]
            del remaining_individuals_dict[individual_id]

        logger.debug(str(len(sample_id_to_individual_record)) + " matched individual ids", user)

        remaining_sample_ids -= set(sample_id_to_individual_record.keys())
        if raise_no_match_error and len(remaining_sample_ids) == len(sample_ids):
            raise ValueError(
                'None of the individuals or samples in the project matched the {} expected sample id(s)'.format(
                    len(sample_ids)
                ))
        if raise_unmatched_error_template and remaining_sample_ids:
            raise ValueError(raise_unmatched_error_template.format(sample_ids=(', '.join(sorted(remaining_sample_ids)))))

        # create new Sample records for Individual records that matches
        new_samples = [
            Sample(
                guid='S{}_{}'.format(random.randint(10**9, 10**10), sample_id)[:Sample.MAX_GUID_SIZE], # nosec
                sample_id=sample_id,
                sample_type=sample_type,
                dataset_type=dataset_type,
                elasticsearch_index=elasticsearch_index,
                data_source=data_source,
                individual=individual,
                created_date=timezone.now(),
                loaded_date=loaded_date or timezone.now(),
            ) for sample_id, individual in sample_id_to_individual_record.items()]
        samples += list(Sample.bulk_create(user, new_samples))
        log_model_bulk_update(logger, new_samples, user, 'create')

    included_families = _validate_samples_families(samples, sample_type, dataset_type)

    return samples, included_families, matched_individual_ids, remaining_sample_ids


def _find_matching_sample_records(projects, sample_ids, sample_type, dataset_type, elasticsearch_index):
    """Find and return Samples of the given sample_type and dataset_type whose sample ids are in sample_ids list.
    If elasticsearch_index is provided, will only match samples with the same index or with no index set

    Args:
        project (object): Django ORM project model
        sample_ids (list): a list of sample ids for which to find matching Sample records
        sample_type (string): one of the Sample.SAMPLE_TYPE_* constants
        dataset_type (string): one of the Sample.DATASET_TYPE_* constants
        elasticsearch_index (string): an optional string specifying the index where the dataset is loaded

    Returns:
        dict: sample_id_to_sample_record containing the matching Sample records
    """

    return list(Sample.objects.select_related('individual').filter(
        individual__family__project__in=projects,
        sample_type=sample_type,
        dataset_type=dataset_type,
        sample_id__in=sample_ids,
        elasticsearch_index=elasticsearch_index,
    ))


def _validate_samples_families(samples, sample_type, dataset_type):
    prefetch_related_objects(samples, 'individual__family')
    included_families = {sample.individual.family for sample in samples}

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
    return included_families


def update_variant_samples(samples, user, elasticsearch_index, data_source=None, loaded_date=None,
                            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS, sample_type=Sample.SAMPLE_TYPE_WES):
    if not loaded_date:
        loaded_date = timezone.now()
    updated_samples = [sample.id for sample in samples]

    activated_sample_guids = Sample.bulk_update(user, {
        'elasticsearch_index': elasticsearch_index,
        'data_source': data_source,
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


def match_and_update_samples(
        projects, user, sample_ids, sample_type, elasticsearch_index=None, data_source=None, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        sample_id_to_individual_id_mapping=None, raise_no_match_error=False,
        raise_unmatched_error_template=None,
):
    loaded_date = timezone.now()
    samples, included_families, matched_individual_ids, remaining_sample_ids = match_sample_ids_to_sample_records(
        projects=projects,
        user=user,
        sample_ids=sample_ids,
        elasticsearch_index=elasticsearch_index,
        data_source=data_source,
        sample_type=sample_type,
        dataset_type=dataset_type,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        loaded_date=loaded_date,
        raise_no_match_error=raise_no_match_error,
        raise_unmatched_error_template=raise_unmatched_error_template,
    )

    activated_sample_guids, inactivated_sample_guids = update_variant_samples(
        samples, user, elasticsearch_index, data_source, loaded_date, dataset_type, sample_type)

    family_guids_to_update = [
        family.guid for family in included_families if family.analysis_status == Family.ANALYSIS_STATUS_WAITING_FOR_DATA
    ]
    Family.bulk_update(
        user, {'analysis_status': Family.ANALYSIS_STATUS_ANALYSIS_IN_PROGRESS}, guid__in=family_guids_to_update)

    # refresh sample models to get updated values
    samples = Sample.objects.filter(id__in=[s.id for s in samples])

    return samples, matched_individual_ids, activated_sample_guids, inactivated_sample_guids, family_guids_to_update, remaining_sample_ids

def _parse_tsv_row(row):
    return [s.strip().strip('"') for s in row.rstrip('\n').split('\t')]

RNA_OUTLIER_COLUMNS = {'geneID': 'gene_id', 'pValue': 'p_value', 'padjust': 'p_adjust', 'zScore': 'z_score'}

SAMPLE_ID_COL = 'sample_id'
GENE_ID_COL = 'gene_id'
TPM_COL = 'TPM'
TISSUE_COL = 'tissue'
INDIV_ID_COL = 'individual_id'
TPM_HEADER_COLS = [SAMPLE_ID_COL, GENE_ID_COL, TISSUE_COL, TPM_COL]

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

        parsed = {GENE_ID_COL: row[GENE_ID_COL], 'tpm': row[TPM_COL]}
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
            existing_data = samples_by_id[sample_id].get(gene_id)
            if existing_data and existing_data != row_dict:
                raise ValueError(
                    f'Error in {sample_id} data for {gene_id}: mismatched entries {existing_data} and {row_dict}')

            indiv_id = row_dict.pop(INDIV_ID_COL, None)
            if indiv_id and sample_id not in sample_id_to_individual_id_mapping:
                sample_id_to_individual_id_mapping[sample_id] = indiv_id

            samples_by_id[sample_id][gene_id] = row_dict

    message = f'Parsed {len(samples_by_id)} RNA-seq samples'
    info = [message]
    logger.info(message, user)

    data_source = file_path.split('/')[-1].split('_-_')[-1]
    samples, _, _, _, _, remaining_sample_ids = match_and_update_samples(
        projects=Project.objects.filter(projectcategory__name=ANALYST_PROJECT_CATEGORY),
        user=user,
        sample_ids=samples_by_id.keys(),
        data_source=data_source,
        sample_type=Sample.SAMPLE_TYPE_RNA,
        sample_id_to_individual_id_mapping=sample_id_to_individual_id_mapping,
        raise_unmatched_error_template=None if ignore_extra_samples else 'Unable to find matches for the following samples: {sample_ids}'
    )

    warnings = []
    if validate_samples:
        samples = validate_samples(samples, sample_id_to_tissue_type, warnings)

    # Delete old data
    individual_db_ids = {s.individual_id for s in samples}
    to_delete = model_cls.objects.filter(sample__individual_id__in=individual_db_ids).exclude(sample__data_source=data_source)
    if to_delete:
        prefetch_related_objects(to_delete, 'sample')
        logger.info(f'delete {len(to_delete)} {model_cls.__name__}s', user, db_update={
            'dbEntity': model_cls.__name__, 'numEntities': len(to_delete), 'updateType': 'bulk_delete',
            'parentEntityIds': list({model.sample.guid for model in to_delete}),
        })
        to_delete.delete()

    loaded_sample_ids = set(model_cls.objects.filter(sample__in=samples).values_list('sample_id', flat=True).distinct())
    samples_to_load = {
        sample: samples_by_id[sample.sample_id] for sample in samples if sample.id not in loaded_sample_ids
    }

    prefetch_related_objects(list(samples_to_load.keys()), 'individual__family__project')
    projects = {sample.individual.family.project.name for sample in samples_to_load}
    project_names = ', '.join(sorted(projects))
    message = f'Attempted data loading for {len(samples_to_load)} RNA-seq samples in the following {len(projects)} projects: {project_names}'
    info.append(message)
    logger.info(message, user)

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
