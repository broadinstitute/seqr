
# b38 - gs://gmkf_engle_callset/900Genomes_full.vcf.gz
# b38 - gs://vep-test/APY-001.vcf.bgz
# b37 - ? - gs://winters/v33.winters.vcf.bgz

# python manage.py add_vcf -t WES -g 37 R0390_1000_genomes_demo  gs://seqr-hail/test-data/1kg.subset_10k.vcf.bgz
#                                                                gs://seqr-hail/test-data/1kg.subset_10k.vep.vds
# python manage.py add_vcf -t WGS -g 38 R0396_engle_2_sample gs://vep-test/APY-001.vcf.bgz
# python manage.py add_vcf -t WGS -g 38 R0397_engle_900 gs://seqr-hail/datasets/GRCh38/900Genomes_full.vcf.gz


# gs://fc-4c1c7765-2de2-4214-ac41-dc10bbcbb55b/mrose/APY-001_blood.cram
# gs://fc-4c1c7765-2de2-4214-ac41-dc10bbcbb55b/mrose/APY-001_tissue.cram

# gs://seqr-hail/test-data/combined-vep-APY-001_subset.vcf.bgz

import logging
import os

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from reference_data.models import GENOME_VERSION_CHOICES
from seqr.models import Project, Sample, Dataset
from seqr.utils.file_utils import does_file_exist, file_iter, inputs_older_than_outputs, \
    copy_file
from seqr.utils.hail_utils import HailRunner
from seqr.views.apis.dataset_api import get_or_create_dataset, link_dataset_to_sample_records

from seqr.views.apis.individual_api import add_or_update_individuals_and_families, \
    export_individuals
from seqr.views.apis.samples_api import match_sample_ids_to_sample_records
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table
from settings import PROJECT_DATA_DIR

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Adds a VCF to a project and loads the variants"""

    def add_arguments(self, parser):
        parser.add_argument("-t", "--sample-type", choices=[k for k, v in Sample.SAMPLE_TYPE_CHOICES],
            help="Type of sequencing that was used to generate this data", required=True)
        parser.add_argument("-g", "--genome-version", help="Genome version 37 or 38", choices=[c[0] for c in GENOME_VERSION_CHOICES], required=True)
        parser.add_argument("--validate-only", action="store_true", help="Only validate the vcf, and don't load it or create any meta-data records.")
        parser.add_argument("--max-edit-distance-for-id-match", help="Specify an edit distance > 0 to allow for non-exact matches between VCF sample ids and Individual ids.", type=int, default=0)
        parser.add_argument("-p", "--pedigree-file", help="(optional) Format: .fam, .xls. These individuals will be added (or updated if they're already in the project) before adding the VCF.")
        parser.add_argument("-e", "--export-pedigree-file-template", help="(optional) Export a pedigree file template for any new VCF samples ids.")
        parser.add_argument("-d", "--dataset-id", help="(optional) The dataset id to use for this VCF. If not specified, a new dataset record will be created, with dataset id computed from the vcf filename, file size, and other properties.")
        parser.add_argument("project_id", help="Project to which this VCF should be added (eg. R0202_tutorial)")
        parser.add_argument("vcf_path", help="Variant callset file path")

    def handle(self, *args, **options):

        analysis_type = Dataset.ANALYSIS_TYPE_VARIANT_CALLS

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

        # look up project id and validate other args
        try:
            project = Project.objects.get(guid=project_guid)
        except ObjectDoesNotExist:
            raise CommandError("Invalid project id: %(project_guid)s" % locals())

        if project.genome_version != genome_version:
            raise CommandError("Genome version %s doesn't match the project's genome version which is %s" % (genome_version, project.genome_version))

        if pedigree_file_path and not os.path.isfile(pedigree_file_path):
            raise CommandError("Can't open pedigree file: %(pedigree_file)s" % locals())

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

        vcf_sample_ids_to_sample_records = match_sample_ids_to_sample_records(
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
                    if vcf_sample_id in vcf_sample_ids_to_sample_records:
                        continue

                    family_id = individual_id = vcf_sample_id
                    out_f.write("%s\n" % ("\t".join([family_id, individual_id, '', '', '', ''],)))

        if len(vcf_sample_ids_to_sample_records) == 0:
            all_vcf_sample_id_count = len(vcf_sample_ids)
            all_project_sample_id_count = len(Sample.objects.filter(individual__family__project=project, sample_type=sample_type))
            logger.info(("No matches found between the %(all_vcf_sample_id_count)s sample id(s) in the VCF and "
                "the %(all_project_sample_id_count)s %(sample_type)s sample id(s) in %(project_guid)s") % locals())
            return

        if validate_only:
            return

         # retrieve or create Dataset record and link it to sample(s)
        dataset = get_or_create_dataset(
            analysis_type=analysis_type,
            source_file_path=vcf_path,
            project=project,
            dataset_id=dataset_id,
        )

        link_dataset_to_sample_records(dataset, vcf_sample_ids_to_sample_records.values())

        # check if all VCF samples loaded already
        vcf_sample_ids = set(vcf_sample_ids_to_sample_records.keys())
        existing_sample_ids = set([s.sample_id for s in dataset.samples.all()])
        if dataset.is_loaded and len(vcf_sample_ids - existing_sample_ids) == 0:
            logger.info("All %s samples in this VCF have already been loaded" % len(vcf_sample_ids))
            return

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
    genome_version = dataset.project.genome_version
    genome_version_label="GRCh%s" % genome_version

    dataset_directory = os.path.join(PROJECT_DATA_DIR, "%(genome_version_label)s/%(dataset_id)s" % locals())
    raw_vcf_path = "%(dataset_directory)s/%(source_filename)s" % locals()
    vep_annotated_vds_path = "%(dataset_directory)s/%(dataset_id)s.vep.vds" % locals()

    if not inputs_older_than_outputs([source_file_path], [raw_vcf_path], label="copy step: "):
        logger.info("Copy step: copying %(source_file_path)s to %(raw_vcf_path)s" % locals())
        copy_file(source_file_path, raw_vcf_path)

    #hail_runner = HailRunner(dataset.dataset_id, dataset.project.genome_version)
    #hail_runner.initialize()

    with HailRunner(dataset.dataset_id, dataset.project.genome_version) as hail_runner:
        vds_file = os.path.join(vep_annotated_vds_path, "metadata.json.gz")  # stat only works on files, not directories
        if not inputs_older_than_outputs([raw_vcf_path], [vds_file], label="vep annotation step: "):
            logger.info("VEP annotation step: annotating %(raw_vcf_path)s and outputing to %(vep_annotated_vds_path)s" % locals())
            hail_runner.run_vep(raw_vcf_path, vep_annotated_vds_path)

        logger.info("Export to elasticsearch step: exporting %(vep_annotated_vds_path)s to elasticsearch" % locals())
        hail_runner.export_to_elasticsearch(vep_annotated_vds_path, dataset.dataset_id, dataset.analysis_type, genome_version)
