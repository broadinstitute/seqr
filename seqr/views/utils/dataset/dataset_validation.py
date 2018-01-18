import logging

from django.core.exceptions import ObjectDoesNotExist

from seqr.models import Project, Sample, Dataset
from seqr.utils.file_utils import does_file_exist, file_iter, get_file_stats
from seqr.views.utils.dataset.dataset_utils import get_dataset, get_or_create_elasticsearch_dataset, \
    link_dataset_to_sample_records
from seqr.views.apis.samples_api import match_sample_ids_to_sample_records

logger = logging.getLogger(__name__)


def add_dataset(
    project,
    sample_type,
    analysis_type,
    genome_version,
    dataset_path,
    max_edit_distance=0,
    dataset_id=None,
    name=None,
    description=None,
    ignore_extra_samples_in_callset=False):

    """Validates the given dataset.
    Args:
        project (object):
        sample_type (string):
        analysis_type (string):
        genome_version (string):
        dataset_path (string):
        max_edit_distance (int):
        dataset_id (string):
        ignore_extra_samples_in_callset (bool):
    Return:
        (errors, warnings, info) tuple

    Dataset.ANALYSIS_TYPE_VARIANT_CALLS
    """
    #elasticsearch_host = options["elasticsearch_host"]
    #elasticsearch_index = options["elasticsearch_index"]
    #is_loaded = options["is_loaded"]

    # check args
    errors = []
    warnings = []
    info = []

    # basic file path checks
    if analysis_type == Dataset.ANALYSIS_TYPE_VARIANT_CALLS:
        if not dataset_path.endswith(".vcf.gz") and not dataset_path.endswith(".vds"):
            errors.append("Dataset path must end with .vcf.gz or .vds")
    elif analysis_type == Dataset.ANALYSIS_TYPE_ALIGNMENT:
        if not any([dataset_path.endswith(suffix) for suffix in ('.txt', '.tsv', '.xls', '.xlsx')]):
            errors.append("BAM / CRAM table must have a .txt or .xls extension")
    else:
        errors.append("dataset type not supported: %s" % (analysis_type,))

    if errors:
        return errors, warnings, info

    # check that dataset file exists
    try:
        dataset_file = does_file_exist(dataset_path)
        if dataset_file is None:
            errors.append("Unable to access %s" % (dataset_path,))
        else:
            # check that dataset_path is accessible
            dataset_file_stats = get_file_stats(dataset_path)
            if dataset_file_stats is None:
                errors.append("Unable to access %s" % (dataset_path,))
    except Exception as e:
        errors.append("dataset path error: " + str(e))

    if errors:
        return errors, warnings, info

    # validate dataset contents
    if analysis_type == Dataset.ANALYSIS_TYPE_VARIANT_CALLS:
        # validate VCF and get sample ids
        try:
            all_vcf_sample_ids = _validate_vcf(dataset_path, sample_type=sample_type, genome_version=genome_version)
        except ValueError as e:
            errors.append(str(e))
            return errors, warnings, info

        matched_sample_id_to_sample_record = match_sample_ids_to_sample_records(
            project,
            sample_ids=all_vcf_sample_ids,
            sample_type=sample_type,
            max_edit_distance=max_edit_distance,
            create_sample_records=True,
        )

        if not ignore_extra_samples_in_callset and len(matched_sample_id_to_sample_record) < len(all_vcf_sample_ids):
            errors.append("Matches not found for VCF sample ids: " +
                ", ".join(set(all_vcf_sample_ids) - set(matched_sample_id_to_sample_record.keys())) +
                ". Select the 'Ignore extra samples in callset' checkbox to ignore this.")

        if len(matched_sample_id_to_sample_record) == 0:
            errors.append("None of the individuals or samples in the project matched the %(all_vcf_sample_id_count)s sample id(s) in the VCF" % locals())
            return errors, warnings, info

            # if Dataset record exists, retrieve it and check if it's already been loaded previously

        # retrieve or create Dataset record and link it to sample(s)
        dataset = get_or_create_elasticsearch_dataset(
            project=project,
            analysis_type=analysis_type,
            genome_version=genome_version,
            source_file_path=dataset_path,
            elasticsearch_index=dataset_id,
            is_loaded=dataset_id is not None,
        )

        dataset.name = name
        dataset.description = description
        dataset.save()

        link_dataset_to_sample_records(dataset, matched_sample_id_to_sample_record.values())

        # check if all VCF samples loaded already - TODO update this?
        vcf_sample_ids = set(matched_sample_id_to_sample_record.keys())
        existing_sample_ids = set([s.sample_id for s in dataset.samples.all()])
        if dataset.is_loaded and len(vcf_sample_ids - existing_sample_ids) == 0:
            info.append("All %s samples in this VCF have already been loaded" % len(vcf_sample_ids))
            return errors, warnings, info
        elif not dataset.is_loaded:
            info.append("Dataset not loaded. Loading...")
        elif len(vcf_sample_ids - existing_sample_ids) != 0:
            info.append("Data will be loaded for these samples: %s" % (vcf_sample_ids - existing_sample_ids, ))

    return errors, warnings, info



def validate_dataset(project, sample_type, analysis_type, genome_version, dataset_path, max_edit_distance=0, dataset_id=None):
    """Validates the given dataset.
    Args:
        project (object):
        sample_type (string):
        analysis_type (string):
        genome_version (string):
        dataset_path (string):
        max_edit_distance (int):
        dataset_id (string):
    Return:
        (errors, warnings, info) tuple

    Dataset.ANALYSIS_TYPE_VARIANT_CALLS
    """
    #elasticsearch_host = options["elasticsearch_host"]
    #elasticsearch_index = options["elasticsearch_index"]
    #is_loaded = options["is_loaded"]

    # check args
    errors = []
    warnings = []
    info = []

    # basic file path checks
    if analysis_type == Dataset.ANALYSIS_TYPE_VARIANT_CALLS:
        if not dataset_path.endswith(".vcf.gz") and not dataset_path.endswith(".vds"):
            errors.append("Dataset path must end with .vcf.gz or .vds")
    elif analysis_type == Dataset.ANALYSIS_TYPE_ALIGNMENT:
        if not any([dataset_path.endswith(suffix) for suffix in ('.txt', '.tsv', '.xls', '.xlsx')]):
            errors.append("BAM / CRAM table must have a .txt or .xls extension")
    else:
        errors.append("dataset type not supported: %s" % (analysis_type,))

    if errors:
        return errors, warnings, info

    # check that dataset file exists
    try:
        dataset_file = does_file_exist(dataset_path)
        if dataset_file is None:
            errors.append("Unable to access %s" % (dataset_path,))
        else:
            # check that dataset_path is accessible
            dataset_file_stats = get_file_stats(dataset_path)
            if dataset_file_stats is None:
                errors.append("Unable to access %s" % (dataset_path,))
    except Exception as e:
        errors.append("dataset path error: " + str(e))

    if errors:
        return errors, warnings, info

    # validate dataset contents
    if analysis_type == Dataset.ANALYSIS_TYPE_VARIANT_CALLS:
        # validate VCF and get sample ids
        try:
            sample_ids = _validate_vcf(dataset_path, sample_type=sample_type, genome_version=genome_version)
        except ValueError as e:
            errors.append(str(e))
            return errors, warnings, info

        matched_sample_id_to_sample_record = match_sample_ids_to_sample_records(
            project,
            sample_ids=sample_ids,
            sample_type=sample_type,
            max_edit_distance=max_edit_distance,
        )

        if len(matched_sample_id_to_sample_record) == 0:
            all_vcf_sample_id_count = len(sample_ids)
            all_project_sample_id_count = len(Sample.objects.filter(individual__family__project=project, sample_type=sample_type))
            errors.append("None of the individuals or samples in the project matched the %(all_vcf_sample_id_count)s sample id(s) in the VCF" % locals())
            return errors, warnings, info

         # if Dataset record exists, retrieve it and check if it's already been loaded previously
        try:
            dataset = get_dataset(
                project=project,
                analysis_type=analysis_type,
                genome_version=genome_version,
                source_file_path=dataset_path,
                #elasticsearch_host=elasticsearch_host,
                #elasticsearch_index=elasticsearch_index,
                #is_loaded=is_loaded,
            )
        except ObjectDoesNotExist as e:
            logger.warning("No existing dataset found")

        # check if all VCF samples loaded already - TODO update this?
        vcf_sample_ids = set(matched_sample_id_to_sample_record.keys())
        existing_sample_ids = set([s.sample_id for s in dataset.samples.all()])
        if dataset.is_loaded and len(vcf_sample_ids - existing_sample_ids) == 0:
            info.append("All %s samples in this VCF have already been loaded" % len(vcf_sample_ids))
            return errors, warnings, info
        elif not dataset.is_loaded:
            info.append("Dataset not loaded. Loading...")
        elif len(vcf_sample_ids - existing_sample_ids) != 0:
            info.append("Data will be loaded for these samples: %s" % (vcf_sample_ids - existing_sample_ids, ))

    return errors, warnings, info


def _validate_vcf(vcf_path, sample_type=None, genome_version=None):
    if not vcf_path or not isinstance(vcf_path, basestring):
        raise ValueError("Invalid vcf_path arg: %(vcf_path)s" % locals())

    if not does_file_exist(vcf_path):
        raise ValueError("%(vcf_path)s not found" % locals())

    header_line = None
    for i, line in enumerate(file_iter(vcf_path)):
        if line.startswith("#CHROM"):
            header_line = line
            break
        if line.startswith("#"):
            continue
        else:
            break

        if i > 20000:
            break  # there's no way header is this long

    if not header_line:
        raise ValueError("Unexpected VCF header. #CHROM not found before line: " + line)

    # TODO if annotating using gcloud, check whether dataproc has access to file

    # TODO check header, sample_type, genome_version
    header_fields = header_line.strip().split('\t')
    sample_ids = header_fields[9:]

    return sample_ids
