import logging
import elasticsearch_dsl
from django.utils import timezone
import random

from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.utils import get_es_client, get_index_metadata
from seqr.utils.file_utils import file_iter, does_file_exist
from seqr.utils.logging_utils import log_model_bulk_update
from seqr.views.utils.file_utils import parse_file

logger = logging.getLogger(__name__)

SAMPLE_FIELDS_MAP = {
    Sample.DATASET_TYPE_VARIANT_CALLS: 'samples_num_alt_1',
    Sample.DATASET_TYPE_SV_CALLS: 'samples',
}


def get_elasticsearch_index_samples(elasticsearch_index, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS):
    es_client = get_es_client()

    index_metadata = get_index_metadata(elasticsearch_index, es_client).get(elasticsearch_index)

    s = elasticsearch_dsl.Search(using=es_client, index=elasticsearch_index)
    s = s.params(size=0)
    s.aggs.bucket('sample_ids', elasticsearch_dsl.A('terms', field=SAMPLE_FIELDS_MAP[dataset_type], size=10000))
    response = s.execute()
    return [agg['key'] for agg in response.aggregations.sample_ids.buckets], index_metadata


def validate_index_metadata(index_metadata, project, elasticsearch_index, genome_version=None,
                            dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS):
    metadata_fields = ['genomeVersion', 'sampleType', 'sourceFilePath']
    if any(field not in (index_metadata or {}) for field in metadata_fields):
        raise ValueError("Index metadata must contain fields: {}".format(', '.join(metadata_fields)))

    sample_type = index_metadata['sampleType']
    if sample_type not in {choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES}:
        raise Exception("Sample type not supported: {}".format(sample_type))

    if index_metadata['genomeVersion'] != (genome_version or project.genome_version):
        raise Exception('Index "{0}" has genome version {1} but this project uses version {2}'.format(
            elasticsearch_index, index_metadata['genomeVersion'], project.genome_version
        ))

    dataset_path = index_metadata['sourceFilePath']
    dataset_suffixes = ('.vds', '.vcf.gz', '.vcf.bgz', '.bed')
    if not dataset_path.endswith(dataset_suffixes):
        raise Exception("Variant call dataset path must end with .vcf.gz or .vds or .bed")

    if index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS) != dataset_type:
        raise Exception('Index "{0}" has dataset type {1} but expects {2}'.format(
            elasticsearch_index, index_metadata.get('datasetType', Sample.DATASET_TYPE_VARIANT_CALLS), dataset_type
        ))


def validate_alignment_dataset_path(dataset_path):
    if not does_file_exist(dataset_path):
        raise Exception('Error accessing "{}"'.format(dataset_path))


def load_mapping_file(mapping_file_path):
    file_content = parse_file(mapping_file_path, file_iter(mapping_file_path))
    return _load_mapping_file(file_content)


def _load_mapping_file(file_content):
    id_mapping = {}
    for line in file_content:
        if len(line) != 2:
            raise ValueError("Must contain 2 columns: " + ', '.join(line))
        id_mapping[line[0]] = line[1]
    return id_mapping


def match_sample_ids_to_sample_records(
        project,
        user,
        sample_ids,
        sample_type,
        dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS,
        elasticsearch_index=None,
        create_sample_records=True,
        sample_id_to_individual_id_mapping=None,
        loaded_date=None,
    ):
    """Goes through the given list of sample_ids and finds existing Sample records of the given
    sample_type and dataset_type with ids from the list. For sample_ids that aren't found to have existing Sample
    records, it looks for Individual records that have an individual_id that either exactly or
    approximately equals one of the sample_ids in the list or is contained in the optional
    sample_id_to_individual_id_mapping and optionally creates new Sample records for these.

    Args:
        project (object): Django ORM project model
        user (object): Django ORM User model
        sample_ids (list): a list of sample ids for which to find matching Sample records
        sample_type (string): one of the Sample.SAMPLE_TYPE_* constants
        dataset_type (string): one of the Sample.DATASET_TYPE_* constants
        elasticsearch_index (string): an optional string specifying the index where the dataset is loaded
        max_edit_distance (int): max permitted edit distance for approximate matches
        create_sample_records (bool): whether to create new Sample records for sample_ids that
            don't match existing Sample records, but do match individual_id's of existing
            Individual records.
        sample_id_to_individual_id_mapping (object): Mapping between sample ids and their corresponding individual ids

    Returns:
        tuple:
            [0] dict: sample_id_to_sample_record containing the matching Sample records (including any
            newly-created ones)
            [1] array: array of the sample_ids of any samples that were created
    """

    sample_id_to_sample_record = find_matching_sample_records(
        project, sample_ids, sample_type, dataset_type, elasticsearch_index
    )
    logger.info(str(len(sample_id_to_sample_record)) + " exact sample record matches")

    remaining_sample_ids = set(sample_ids) - set(sample_id_to_sample_record.keys())
    if len(remaining_sample_ids) > 0:
        already_matched_individual_ids = {
            sample.individual.individual_id for sample in sample_id_to_sample_record.values()
        }

        remaining_individuals_dict = {
            i.individual_id: i for i in
            Individual.objects.filter(family__project=project).exclude(individual_id__in=already_matched_individual_ids)
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

        logger.info(str(len(sample_id_to_individual_record)) + " matched individual ids")

        # create new Sample records for Individual records that matches
        if create_sample_records:
            new_samples = [
                Sample(
                    guid='S{}_{}'.format(random.randint(10**9, 10**10), sample_id)[:Sample.MAX_GUID_SIZE],
                    sample_id=sample_id,
                    sample_type=sample_type,
                    dataset_type=dataset_type,
                    elasticsearch_index=elasticsearch_index,
                    individual=individual,
                    created_date=timezone.now(),
                    loaded_date=loaded_date or timezone.now(),
                ) for sample_id, individual in sample_id_to_individual_record.items()]
            sample_id_to_sample_record.update({
                sample.sample_id: sample for sample in Sample.bulk_create(user, new_samples)
            })
            log_model_bulk_update(logger, new_samples, user, 'create')

    return sample_id_to_sample_record


def find_matching_sample_records(project, sample_ids, sample_type, dataset_type, elasticsearch_index):
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

    sample_id_to_sample_record = {}
    sample_query = Sample.objects.select_related('individual').filter(
        individual__family__project=project,
        sample_type=sample_type,
        dataset_type=dataset_type,
        sample_id__in=sample_ids
    )
    if elasticsearch_index:
        sample_query = sample_query.filter(elasticsearch_index=elasticsearch_index)
    for sample in sample_query:
        sample_id_to_sample_record[sample.sample_id] = sample

    return sample_id_to_sample_record
