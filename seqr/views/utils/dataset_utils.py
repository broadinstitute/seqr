import logging
import json
import elasticsearch_dsl
from django.utils import timezone
from django.db.models.query_utils import Q

from seqr.views.apis.igv_api import proxy_to_igv
from seqr.models import Sample, Individual
from seqr.utils.es_utils import get_es_client, get_index_metadata
from seqr.utils import file_utils
from seqr.views.utils.file_utils import load_uploaded_file, parse_file

logger = logging.getLogger(__name__)


def get_elasticsearch_index_samples(elasticsearch_index):
    es_client = get_es_client()

    index_metadata = get_index_metadata(elasticsearch_index, es_client).get(elasticsearch_index)

    s = elasticsearch_dsl.Search(using=es_client, index=elasticsearch_index)
    s = s.params(size=0)
    s.aggs.bucket('sample_ids', elasticsearch_dsl.A('terms', field='samples_num_alt_1', size=10000))
    response = s.execute()
    return [agg['key'] for agg in response.aggregations.sample_ids.buckets], index_metadata


def validate_index_metadata(index_metadata, project, elasticsearch_index):
    metadata_fields = ['genomeVersion', 'sampleType', 'sourceFilePath']
    if any(field not in (index_metadata or {}) for field in metadata_fields):
        raise ValueError("Index metadata must contain fields: {}".format(', '.join(metadata_fields)))

    sample_type = index_metadata['sampleType']
    if sample_type not in {choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES}:
        raise Exception("Sample type not supported: {}".format(sample_type))

    if index_metadata['genomeVersion'] != project.genome_version:
        raise Exception('Index "{0}" has genome version {1} but this project uses version {2}'.format(
            elasticsearch_index, index_metadata['genomeVersion'], project.genome_version
        ))

    dataset_path = index_metadata['sourceFilePath']
    if dataset_path.endswith('.vds'):
        dataset_path += '/metadata.json.gz'
        _validate_dataset_path(dataset_path)
        _validate_vcf_metadata(dataset_path)
    elif dataset_path.endswith(".vcf.gz"):
        _validate_dataset_path(dataset_path)
        _validate_vcf(dataset_path)
    else:
        raise Exception("Variant call dataset path must end with .vcf.gz or .vds")


def validate_alignment_dataset_path(dataset_path):
    headers = {'Range': 'bytes=0-100'} if dataset_path.endswith('.bam') else {}
    resp = proxy_to_igv(dataset_path, {'options': '-b,-H'}, method='GET', scheme='http', headers=headers)
    if resp.status_code >= 400 or (resp.get('Content-Type') != 'application/octet-stream' and resp.get('Content-Encoding') != 'gzip'):
        raise Exception('Error accessing "{}": {}'.format(dataset_path, resp.content))


def _validate_dataset_path(dataset_path):
    try:
        dataset_file = file_utils.does_file_exist(dataset_path)
        if dataset_file is None:
            raise Exception('"{}" not found'.format(dataset_path))
        # check that dataset_path is accessible
        dataset_file_stats = file_utils.get_file_stats(dataset_path)
        if dataset_file_stats is None:
            raise Exception('Unable to access "{}"'.format(dataset_path))
    except Exception as e:
        raise Exception("Dataset path error: " + str(e))


def _validate_vcf(vcf_path):
    header_line = None
    for line in file_utils.file_iter(vcf_path):
        if line.startswith("#CHROM"):
            header_line = line
            break
        if line.startswith("#"):
            continue
        else:
            break

    if not header_line:
        raise Exception("Unexpected VCF header. #CHROM not found before line: {}".format(line))

    header_fields = header_line.strip().split('\t')
    sample_ids = header_fields[9:]

    if not sample_ids:
        raise Exception('No samples found in VCF "{}"'.format(vcf_path))


def _validate_vcf_metadata(vcf_path):
    metadata = '\n'.join([line for line in file_utils.file_iter(vcf_path)])
    if 'sample_annotations' not in json.loads(metadata):
        raise Exception('No samples found in "{}"'.format(vcf_path))


def load_mapping_file(mapping_file_path):
    file_content = parse_file(mapping_file_path, file_utils.file_iter(mapping_file_path))
    return _load_mapping_file(file_content)


def load_uploaded_mapping_file(mapping_file_id):
    file_content = load_uploaded_file(mapping_file_id)
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
        sample_ids,
        sample_type,
        dataset_type,
        elasticsearch_index=None,
        create_sample_records=True,
        sample_id_to_individual_id_mapping=None,
    ):
    """Goes through the given list of sample_ids and finds existing Sample records of the given
    sample_type and dataset_type with ids from the list. For sample_ids that aren't found to have existing Sample
    records, it looks for Individual records that have an individual_id that either exactly or
    approximately equals one of the sample_ids in the list or is contained in the optional
    sample_id_to_individual_id_mapping and optionally creates new Sample records for these.

    Args:
        project (object): Django ORM project model
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
            for sample_id, individual in sample_id_to_individual_record.items():
                new_sample = Sample.objects.create(
                    sample_id=sample_id,
                    sample_type=sample_type,
                    dataset_type=dataset_type,
                    elasticsearch_index=elasticsearch_index,
                    individual=individual,
                    sample_status=Sample.SAMPLE_STATUS_LOADED,
                    loaded_date=timezone.now(),
                )
                sample_id_to_sample_record[sample_id] = new_sample

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

    if len(sample_ids) == 0:
        return {}

    sample_id_to_sample_record = {}
    sample_query = Sample.objects.select_related('individual').filter(
        individual__family__project=project,
        sample_type=sample_type,
        dataset_type=dataset_type,
        sample_id__in=sample_ids
    )
    if elasticsearch_index:
        sample_query = sample_query.filter(
            Q(elasticsearch_index=elasticsearch_index) |
            (Q(elasticsearch_index__isnull=True) & ~Q(sample_status=Sample.SAMPLE_STATUS_LOADED))
        )
    for sample in sample_query:
        sample_id_to_sample_record[sample.sample_id] = sample

    return sample_id_to_sample_record
