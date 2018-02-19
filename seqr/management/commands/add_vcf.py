import logging
import os

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from reference_data.models import GENOME_VERSION_CHOICES
from seqr.models import Project, Sample, Dataset
from seqr.utils.file_utils import does_file_exist, file_iter, inputs_older_than_outputs, \
    copy_file
from seqr.views.utils.dataset.dataset_utils import link_dataset_to_sample_records, \
    get_or_create_elasticsearch_dataset

from seqr.views.apis.individual_api import add_or_update_individuals_and_families
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
        parser.add_argument('--remap-sample-ids', help="Filepath containing 2 tab-separated columns: current sample id and desired sample id")
        parser.add_argument("--max-edit-distance-for-id-match", help="Specify an edit distance > 0 to allow for non-exact matches between VCF sample ids and Individual ids.", type=int, default=0)
        parser.add_argument("-p", "--pedigree-file", help="(optional) Format: .fam, .xls. These individuals will be added (or updated if they're already in the project) before adding the VCF.")
        parser.add_argument("-e", "--export-pedigree-file-template", help="(optional) Export a pedigree file template for any new VCF samples ids.")
        parser.add_argument("-i", "--elasticsearch-index", help="Elasticsearch index name")
        parser.add_argument("--is-loaded", action="store_true", help="Whether the data is already loaded into Elasticsearch")

        parser.add_argument("project_id", help="Project to which this VCF should be added (eg. R0202_tutorial)")
        parser.add_argument("vcf_path", help="Variant callset file path")

    def handle(self, *args, **options):

        analysis_type = Dataset.ANALYSIS_TYPE_VARIANT_CALLS

        # parse and validate args
        sample_type = options["sample_type"]
        genome_version = options["genome_version"]
        validate_only = options["validate_only"]
        remap_sample_ids = options["remap_sample_ids"]
        max_edit_distance = options["max_edit_distance_for_id_match"]
        pedigree_file_path = options["pedigree_file"]
        export_pedigree_file_template = options["export_pedigree_file_template"]
        project_guid = options["project_id"]
        vcf_path = options["vcf_path"]
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

        if remap_sample_ids:
            if not does_file_exist(remap_sample_ids):
                raise ValueError("File not found: " + remap_sample_ids)

            id_mapping = {}
            for line in file_iter(remap_sample_ids):
                fields = line.strip().split("\t")
                if len(fields) != 2:
                    raise ValueError("Must contain 2 columns: " + str(fields))
                id_mapping[fields[0]] = fields[1]

            remapped_vcf_sample_ids = []
            for sample_id in vcf_sample_ids:
                if sample_id in id_mapping:
                    remapped_vcf_sample_ids.append(id_mapping[sample_id])
                    print("Remapped %s to %s" % (sample_id, id_mapping[sample_id]))
                else:
                    remapped_vcf_sample_ids.append(sample_id)
                    print("No sample id mapping for %s" % sample_id)
                    
            vcf_sample_ids = remapped_vcf_sample_ids

        vcf_sample_ids_to_sample_records = match_sample_ids_to_sample_records(
            project,
            sample_ids=vcf_sample_ids,
            sample_type=sample_type,
            max_edit_distance=max_edit_distance,
            create_sample_records=not validate_only,
        )

        if export_pedigree_file_template:
            with open(export_pedigree_file_template, "w") as out_f:
                out_f.write("#%s\n" % ("\t".join(['family_id', 'individual_id', 'paternal_id', 'maternal_id', 'sex', 'affected_status'],)))
                for vcf_sample_id in vcf_sample_ids:
                    if vcf_sample_id in vcf_sample_ids_to_sample_records:
                        continue

                    family_id = individual_id = vcf_sample_id
                    out_f.write("%s\n" % ("\t".join([family_id, individual_id, '', '', '', ''],)))
            logger.info("Wrote out %(export_pedigree_file_template)s. Exiting..." % locals())
            return

        if len(vcf_sample_ids_to_sample_records) == 0:
            all_vcf_sample_id_count = len(vcf_sample_ids)
            all_project_sample_id_count = len(Sample.objects.filter(individual__family__project=project, sample_type=sample_type))
            logger.info("None of the individuals or samples in the project matched the %(all_vcf_sample_id_count)s sample id(s) in the VCF" % locals())
            return

        # retrieve or create Dataset record and link it to sample(s)
        dataset = get_or_create_elasticsearch_dataset(
            project=project,
            analysis_type=analysis_type,
            genome_version=genome_version,
            source_file_path=vcf_path,
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

    # TODO if annotating using gcloud, check whether dataproc has access to the vcf

    # TODO check header, sample_type, genome_version
    header_fields = header_line.strip().split('\t')
    sample_ids = header_fields[9:]

    return sample_ids
