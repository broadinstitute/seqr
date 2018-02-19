import logging
import os

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from reference_data.models import GENOME_VERSION_CHOICES
from seqr.models import Project, Sample, Dataset
from seqr.utils.file_utils import does_file_exist, file_iter, inputs_older_than_outputs, \
    copy_file
from seqr.utils.hail_utils import HailRunner

from seqr.views.apis.individual_api import add_or_update_individuals_and_families
from seqr.views.apis.samples_api import match_sample_ids_to_sample_records
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table
from settings import PROJECT_DATA_DIR

logger = logging.getLogger(__name__)

def load_dataset(dataset):
    dataset

"""
def add_dataset():
    # parse and validate args
    sample_type = options["sample_type"]
    genome_version = options["genome_version"]
    validate_only = options["validate_only"]
    max_edit_distance = options["max_edit_distance_for_id_match"]
    pedigree_file_path = options["pedigree_file"]
    export_pedigree_file_template = options["export_pedigree_file_template"]
    project_guid = options["project_id"]
    vcf_path = options["vcf_path"]
    dataset_id = options["dataset_id"]
    elasticsearch_host = options["elasticsearch_host"]
    elasticsearch_index = options["elasticsearch_index"]
    is_loaded = options["is_loaded"]

    # look up project id and validate other args
    try:
        project = Project.objects.get(guid=project_guid)
    except ObjectDoesNotExist:
        raise CommandError("Invalid project id: %(project_guid)s" % locals())

    #if project.genome_version != genome_version:
    #    raise CommandError("Genome version %s doesn't match the project's genome version which is %s" % (genome_version, project.genome_version))

    if pedigree_file_path and not os.path.isfile(pedigree_file_path):
        raise CommandError("Can't open pedigree file: %(pedigree_file_path)s" % locals())

    # parse the pedigree file if specified
    if pedigree_file_path:

        input_stream = file_iter(pedigree_file_path)
        json_records, errors, warnings = parse_pedigree_table(pedigree_file_path, input_stream)

        if errors:
            for message in errors:
                logger.error(message)
            raise CommandError("Unable to parse %(pedigree_file_path)s" % locals())

        if warnings:
            for message in warnings:
                logger.warn(message)

        if not validate_only:
            add_or_update_individuals_and_families(project, json_records)

    # validate VCF and get sample ids
    vcf_sample_ids = _validate_vcf(vcf_path, sample_type=sample_type, genome_version=genome_version)

    vcf_sample_id_to_sample_record = match_sample_ids_to_sample_records(
        project,
        sample_ids=vcf_sample_ids,
        sample_type=sample_type,
        max_edit_distance=max_edit_distance,
        create_records_for_new_sample_ids=not validate_only,
    )



    if export_pedigree_file_template:
        with open(export_pedigree_file_template, "w") as out_f:
            out_f.write("#%s\n" % ("\t".join(['family_id', 'individual_id', 'paternal_id', 'maternal_id', 'sex', 'affected_status'],)))
            for vcf_sample_id in vcf_sample_ids:
                if vcf_sample_id in vcf_sample_id_to_sample_record:
                    continue

                family_id = individual_id = vcf_sample_id
                out_f.write("%s\n" % ("\t".join([family_id, individual_id, '', '', '', ''],)))
        logger.info("Wrote out %(export_pedigree_file_template)s. Exiting..." % locals())
        return

    if len(vcf_sample_ids_to_sample_records) == 0:
        all_vcf_sample_id_count = len(vcf_sample_ids)
        all_project_sample_id_count = len(Sample.objects.filter(individual__family__project=project, sample_type=sample_type))
        logger.info(("No matches found between the %(all_vcf_sample_id_count)s sample id(s) in the VCF and "
                     "the %(all_project_sample_id_count)s %(sample_type)s sample id(s) in %(project_guid)s") % locals())
        return


        # retrieve or create Dataset record and link it to sample(s)
    dataset = get_or_create_elasticsearch_dataset(
        project=project,
        analysis_type=analysis_type,
        genome_version=genome_version,
        source_file_path=vcf_path,
        elasticsearch_host=elasticsearch_host,
        elasticsearch_index=elasticsearch_index,
        is_loaded=is_loaded,
    )

    if is_loaded and not dataset.loaded_date:
        dataset.loaded_date=timezone.now()
        dataset.save()

    link_dataset_to_sample_records(dataset, vcf_sample_ids_to_sample_records.values())

    # check if all VCF samples loaded already
    vcf_sample_ids = set(vcf_sample_ids_to_sample_records.keys())
    existing_sample_ids = set([s.sample_id for s in dataset.samples.all()])
    if dataset.is_loaded and len(vcf_sample_ids - existing_sample_ids) == 0:
        logger.info("All %s samples in this VCF have already been loaded" % len(vcf_sample_ids))
        return
    elif not dataset.is_loaded:
        logger.info("Dataset not loaded. %s Loading..." % (is_loaded,))
    elif len(vcf_sample_ids - existing_sample_ids) != 0:
        logger.info("Dataset is loaded but these samples aren't included in the dataset: %s" % (vcf_sample_ids - existing_sample_ids, ))

    # load the VCF
    _load_variants(dataset)

    logger.info("done")


def _validate_vcf(vcf_path, sample_type=None, genome_version=None):
    if not vcf_path or not isinstance(vcf_path, str):
        raise CommandError("Invalid vcf_path arg: %(vcf_path)s" % locals())

    if not does_file_exist(vcf_path):
        raise ValueError("%(vcf_path)s not found" % locals())

    for line in file_iter(vcf_path):
        if line.startswith("#CHROM"):
            header_line = line
            break
        if line.startswith("#"):
            continue
    else:
        raise ValueError("Unexpected VCF header. #CHROM not found before line: " + line)

    # TODO if annotating using gcloud, check whether dataproc has access to file

    # TODO check header, sample_type, genome_version
    header_fields = header_line.strip().split('\t')
    sample_ids = header_fields[9:]

    return sample_ids


def _load_variants(dataset):
    dataset_id = dataset.dataset_id
    source_file_path = dataset.source_file_path
    source_filename = os.path.basename(dataset.source_file_path)
    genome_version = dataset.genome_version
    genome_version_label="GRCh%s" % genome_version

    dataset_directory = os.path.join(PROJECT_DATA_DIR, "%(genome_version_label)s/%(dataset_id)s" % locals())
    raw_vcf_path = "%(dataset_directory)s/%(source_filename)s" % locals()
    vep_annotated_vds_path = "%(dataset_directory)s/%(dataset_id)s.vep.vds" % locals()

    if not inputs_older_than_outputs([source_file_path], [raw_vcf_path], label="copy step: "):
        logger.info("Copy step: copying %(source_file_path)s to %(raw_vcf_path)s" % locals())
        copy_file(source_file_path, raw_vcf_path)

    hail_runner = HailRunner(dataset.dataset_id, dataset.genome_version)
    hail_runner.initialize()

    #with HailRunner(dataset.dataset_id, dataset.project.genome_version) as hail_runner:
    if True:
        vds_file = os.path.join(vep_annotated_vds_path, "metadata.json.gz")  # stat only works on files, not directories
        if not inputs_older_than_outputs([raw_vcf_path], [vds_file], label="vep annotation step: "):
            logger.info("VEP annotation step: annotating %(raw_vcf_path)s and outputing to %(vep_annotated_vds_path)s" % locals())
            hail_runner.run_vep(raw_vcf_path, vep_annotated_vds_path)

        logger.info("Export to elasticsearch step: exporting %(vep_annotated_vds_path)s to elasticsearch" % locals())
        hail_runner.export_to_elasticsearch(vep_annotated_vds_path, dataset.dataset_id, dataset.analysis_type, genome_version)
"""