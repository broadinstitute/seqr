import logging
import elasticsearch_dsl
from elasticsearch import NotFoundError, TransportError
from django.utils import timezone

from seqr.models import Sample
from seqr.utils.es_utils import es_client, VARIANT_DOC_TYPE
from seqr.utils.file_utils import does_file_exist, file_iter, get_file_stats
from seqr.views.apis.samples_api import match_sample_ids_to_sample_records

logger = logging.getLogger(__name__)


def add_dataset(
    project,
    elasticsearch_index,
    sample_type,
    dataset_type,
    dataset_path=None,
    dataset_name=None,
    max_edit_distance=0,
    sample_ids_to_individual_ids_path=None,
    ignore_extra_samples_in_callset=False
):

    """Validates the given dataset.

    Args:
        project (object):
        sample_type (string):
        dataset_type (string):
        genome_version (string):
        dataset_path (string):
        max_edit_distance (int):
        elasticsearch_index (string):
        ignore_extra_samples_in_callset (bool):
    Return:
        (errors, info) tuple
    """

    _validate_inputs(dataset_type=dataset_type, sample_type=sample_type, dataset_path=dataset_path)

    if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
        _add_variant_calls_dataset(
            project=project,
            elasticsearch_index=elasticsearch_index,
            sample_type=sample_type,
            dataset_path=dataset_path,
            dataset_name=dataset_name,
            max_edit_distance=max_edit_distance,
            ignore_extra_samples_in_callset=ignore_extra_samples_in_callset,
            sample_ids_to_individual_ids_path=sample_ids_to_individual_ids_path,
        )
    elif dataset_type == Sample.DATASET_TYPE_READ_ALIGNMENTS:
        _add_read_alignment_dataset(
            project,
            sample_type,
            dataset_path,
            max_edit_distance=max_edit_distance,
            elasticsearch_index=elasticsearch_index,
            ignore_extra_samples_in_callset=ignore_extra_samples_in_callset,
        )


def _add_variant_calls_dataset(
    project,
    elasticsearch_index,
    sample_type,
    dataset_path=None,
    dataset_name=None,
    max_edit_distance=0,
    sample_ids_to_individual_ids_path=None,
    ignore_extra_samples_in_callset=False
):

    dataset_type = Sample.DATASET_TYPE_VARIANT_CALLS

    all_samples = _get_elasticsearch_index_samples(elasticsearch_index)

    if sample_ids_to_individual_ids_path:
        all_samples = _remap_sample_ids(sample_ids_to_individual_ids_path)

    matched_sample_id_to_sample_record, created_samples = match_sample_ids_to_sample_records(
        project=project,
        sample_ids=all_samples,
        sample_type=sample_type,
        dataset_type=dataset_type,
        max_edit_distance=max_edit_distance,
        create_sample_records=True,
    )

    unmatched_samples = set(all_samples) - set(matched_sample_id_to_sample_record.keys())
    if not ignore_extra_samples_in_callset and len(unmatched_samples) > 0:
        raise Exception("Matches not found for ES sample ids: {}. Select the 'Ignore extra samples in callset' checkbox to ignore this.".format(
            ", ".join(set(all_samples) - set(matched_sample_id_to_sample_record.keys()))
        ))

    if len(matched_sample_id_to_sample_record) == 0:
        raise Exception("None of the individuals or samples in the project matched the {} sample id(s) in the elasticsearch index".format(len(all_samples)))

    not_loaded_samples = []
    for sample_id, sample in matched_sample_id_to_sample_record.items():
        sample.elasticsearch_index = elasticsearch_index
        if dataset_path:
            sample.dataset_file_path = dataset_path
        if dataset_name:
            sample.dataset_name = dataset_name
        if sample.sample_status != Sample.SAMPLE_STATUS_LOADED:
            not_loaded_samples.append(sample_id)
            sample.sample_status = Sample.SAMPLE_STATUS_LOADED
            sample.loaded_date = timezone.now()
        sample.save()


def _add_read_alignment_dataset(*args, **kwargs):
    dataset_type = Sample.DATASET_TYPE_READ_ALIGNMENTS

    # TODO


def _get_elasticsearch_index_samples(elasticsearch_index):
    sample_field_suffix = '_num_alt'

    index = elasticsearch_dsl.Index('{}'.format(elasticsearch_index), using=es_client())
    try:
        field_mapping = index.get_field_mapping(fields=['*{}'.format(sample_field_suffix)], doc_type=[VARIANT_DOC_TYPE])
    except NotFoundError:
        raise Exception('Index "{}" not found'.format(elasticsearch_index))
    except TransportError as e:
        raise Exception(e.error)

    variant_field_mapping = field_mapping.get(elasticsearch_index, {}).get('mappings', {}).get(VARIANT_DOC_TYPE)
    if not variant_field_mapping:
        raise Exception('No sample fields found for index "{}"'.format(elasticsearch_index))

    return [key.rstrip(sample_field_suffix) for key in field_mapping[elasticsearch_index]['mappings'].get(VARIANT_DOC_TYPE, {}).keys()]


def _validate_inputs(dataset_type, sample_type, dataset_path):
    # basic sample type checks
    if sample_type not in {choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES}:
        raise Exception("Sample type not supported: {}".format(sample_type))

    if dataset_path:
        # check that dataset file exists if specified
        try:
            dataset_file = does_file_exist(dataset_path)
            if dataset_file is None:
                raise Exception('"{}" not found'.format(dataset_path))
            # check that dataset_path is accessible
            dataset_file_stats = get_file_stats(dataset_path)
            if dataset_file_stats is None:
                raise Exception('Unable to access "{}"'.format(dataset_path))
        except Exception as e:
            raise Exception("Dataset path error: " + str(e))

        # datatset_type-specific checks
        if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
            if not dataset_path.endswith(".vcf.gz") and not dataset_path.endswith(".vds"):
                raise Exception("Variant call dataset path must end with .vcf.gz or .vds")
            _validate_vcf(dataset_path)

        elif dataset_type == Sample.DATASET_TYPE_READ_ALIGNMENTS:
            if not any([dataset_path.endswith(suffix) for suffix in ('.txt', '.tsv', '.xls', '.xlsx')]):
                raise Exception("BAM / CRAM table must have a .txt or .xls extension")

        else:
            raise Exception("Dataset type not supported: {}".format(dataset_type))


def _validate_vcf(vcf_path):
    header_line = None
    for line in file_iter(vcf_path):
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


# TODO for real?
def _remap_sample_ids(sample_ids_to_individual_ids_path):
    if not does_file_exist(sample_ids_to_individual_ids_path):
        return ["File not found: " + sample_ids_to_individual_ids_path]

    id_mapping = {}
    for line in file_iter(sample_ids_to_individual_ids_path):
        fields = line.strip().split("\t")
        if len(fields) != 2:
            raise ValueError("Must contain 2 columns: " + str(fields))
        id_mapping[fields[0]] = fields[1]

    remapped_sample_ids = []
    for sample_id in sample_ids_to_individual_ids_path:
        if sample_id in id_mapping:
            remapped_sample_ids.append(id_mapping[sample_id])
            logger.info("Remapped %s to %s" % (sample_id, id_mapping[sample_id]))
        else:
            remapped_sample_ids.append(sample_id)
            logger.info("No sample id mapping for %s" % sample_id)
    return remapped_sample_ids
