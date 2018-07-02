import logging
import elasticsearch_dsl

from django.utils import timezone

from seqr.models import Sample
from seqr.utils.es_utils import es_client, VARIANT_DOC_TYPE
from seqr.utils.file_utils import does_file_exist, file_iter, get_file_stats
from seqr.views.apis.samples_api import match_sample_ids_to_sample_records

logger = logging.getLogger(__name__)


def add_variant_calls_dataset(
    project,
    elasticsearch_index,
    sample_type,
    dataset_path=None,
    dataset_name=None,
    max_edit_distance=0,
    sample_ids_to_individual_ids_path=None,
    ignore_extra_samples_in_callset=False):

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
    dataset_type = Sample.DATASET_TYPE_VARIANT_CALLS
    info = []

    errors = _validate_inputs(
        dataset_type=dataset_type, sample_type=sample_type, dataset_path=dataset_path
    )
    if errors:
        return errors, info

    all_samples = _get_elasticsearch_index_samples(elasticsearch_index)

    # validate VCF sample ids if specified
    if dataset_path:
        errors, all_vcf_sample_ids = _validate_vcf(dataset_path)
        missing_vcf_samples = set(all_vcf_sample_ids) - set(all_samples)
        if all_vcf_sample_ids and len(missing_vcf_samples) > 0:
            errors.append('Samples in the VCF are missing from the elasticsearch index: {}'.format(', '.join(missing_vcf_samples)))
        if errors:
            return errors, info

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
        errors.append("Matches not found for ES sample ids: " +
            ", ".join(set(all_samples) - set(matched_sample_id_to_sample_record.keys())) +
            ". Select the 'Ignore extra samples in callset' checkbox to ignore this.")

    if len(matched_sample_id_to_sample_record) == 0:
        errors.append("None of the individuals or samples in the project matched the {} sample id(s) in the elasticsearch index".format(len(all_samples)))
        return errors, info

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

    if len(not_loaded_samples) + len(created_samples) == 0:
        info.append("All {} samples in this index have already been loaded".format(len(matched_sample_id_to_sample_record)))
    else:
        info.append("The following sample records were set as loaded: {}".format(', '.join(not_loaded_samples)))
    if len(created_samples) > 0:
        info.append("The following sample records were created: {}".format(', '.join(created_samples)))

    return errors, info


def add_read_alignment_dataset(*args, **kwargs):
    errors = []
    info = []
    dataset_type = Sample.DATASET_TYPE_READ_ALIGNMENTS

    # TODO

    return errors, info


def _get_elasticsearch_index_samples(elasticsearch_index):
    sample_field_suffix = '_num_alt'

    index = elasticsearch_dsl.Index('{}*'.format(elasticsearch_index), using=es_client())
    field_mapping = index.get_field_mapping(fields=['*{}'.format(sample_field_suffix)], doc_type=[VARIANT_DOC_TYPE])

    samples = set()
    for index in field_mapping.values():
        samples.update([key.rstrip(sample_field_suffix) for key in index['mappings'].get(VARIANT_DOC_TYPE, {}).keys()])
    return samples


def _validate_inputs(dataset_type, sample_type, dataset_path):
    errors = []

    # basic sample type checks
    if sample_type not in {choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES}:
        errors.append("Sample type not supported: {}".format(sample_type))

    if dataset_path:
        # basic file path checks
        if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS:
            if not dataset_path.endswith(".vcf.gz") and not dataset_path.endswith(".vds"):
                errors.append("Variant call dataset path must end with .vcf.gz or .vds")
        elif dataset_type == Sample.DATASET_TYPE_READ_ALIGNMENTS:
            if not any([dataset_path.endswith(suffix) for suffix in ('.txt', '.tsv', '.xls', '.xlsx')]):
                errors.append("BAM / CRAM table must have a .txt or .xls extension")
        else:
            errors.append("Dataset type not supported: {}".format(dataset_type))

        # check that dataset file exists if specified
        try:
            dataset_file = does_file_exist(dataset_path)
            if dataset_file is None:
                errors.append("Unable to access {}".format(dataset_path))
            # check that dataset_path is accessible
            dataset_file_stats = get_file_stats(dataset_path)
            if dataset_file_stats is None:
                errors.append("Unable to access {}".format(dataset_path))
        except Exception as e:
            errors.append("Dataset path error: " + str(e))

    return errors


def _validate_vcf(vcf_path):
    if not vcf_path or not isinstance(vcf_path, basestring):
        return ["Invalid vcf_path arg: {}".format(vcf_path)], []

    if not does_file_exist(vcf_path):
        return ["{} not found".format(vcf_path)], []

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
        return ["Unexpected VCF header. #CHROM not found before line: " + line], []

    # TODO if annotating using gcloud, check whether dataproc has access to file

    # TODO check header, sample_type, genome_version
    header_fields = header_line.strip().split('\t')
    sample_ids = header_fields[9:]

    return [], sample_ids


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
