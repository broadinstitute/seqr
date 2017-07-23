import datetime
import logging
import numpy as np
import os

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from reference_data.models import GENOME_VERSION_CHOICES
from seqr.models import Project, Individual, Sample, Dataset
from seqr.utils.file_utils import get_file_stats, does_file_exist, file_iter, inputs_older_than_outputs, \
    copy_file
from seqr.utils.hail_utils import HailRunner

from seqr.views.apis.individual_api import add_or_update_individuals_and_families
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table
from seqr.utils.shell_utils import ask_yes_no_question
from settings import USE_GCLOUD_DATAPROC, PROJECT_DATA_DIR

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Adds a VCF to a project and loads the variants"""

    def add_arguments(self, parser):
        parser.add_argument("-t", "--sample-type", choices=[k for k, v in Sample.SAMPLE_TYPE_CHOICES],
            help="Type of sequencing that was used to generate this data", required=True)
        parser.add_argument("-g", "--genome-version", help="Genome version 37 or 38", choices=[c[0] for c in GENOME_VERSION_CHOICES], required=True)
        parser.add_argument("--only-validate", action="store_true", help="Only validate the vcf, and don't load it or create any meta-data records.")
        parser.add_argument("--max-edit-distance-for-id-match", help="Specify an edit distance > 0 to allow for non-exact matches between VCF sample ids and Individual ids.", type=int, default=0)
        parser.add_argument("-p", "--pedigree-file", help="(optional) Format: .fam, .xls. These individuals will be added (or updated if they're already in the project) before adding the VCF.")
        parser.add_argument("-d", "--dataset-id", help="(optional) The dataset id to use for this VCF. If not specified, a dataset id will be computed based on the vcf filename, file size, and other properties.")
        parser.add_argument("project_id", help="Project to which this VCF should be added (eg. R0202_tutorial)")
        parser.add_argument("vcf_path", help="Variant callset file path")

    def handle(self, *args, **options):

        analysis_type = Dataset.ANALYSIS_TYPE_VARIANT_CALLS

        # parse and validate args
        sample_type = options["sample_type"]
        genome_version = options["genome_version"]
        only_validate = options["only_validate"]
        max_edit_distance = options["max_edit_distance_for_id_match"]
        pedigree_file_path = options["pedigree_file"]
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

            add_or_update_individuals_and_families(project, json_records)

        # validate VCF and get sample ids
        vcf_sample_ids = _validate_vcf(vcf_path, sample_type=sample_type, genome_version=genome_version)

        # compare VCF sample ids to existing Sample record Ids in this project
        vcf_sample_id_to_sample_record = _match_vcf_id_to_sample_id(
            vcf_sample_ids,
            project,
            sample_type,
            max_edit_distance=max_edit_distance,
            only_validate=only_validate,
        )

        # check if a Dataset record already exists for this vcf in this project
        try:
            dataset = Dataset.objects.get(
                analysis_type=analysis_type,
                source_file_path=vcf_path,
                project=project)

            # check if all VCF samples loaded already
            vcf_sample_ids = set(vcf_sample_id_to_sample_record.keys())
            existing_sample_ids = set([s.sample_id for s in dataset.samples.all()])
            if dataset.is_loaded and len(vcf_sample_ids - existing_sample_ids) == 0:
                logger.info("All %s samples in this VCF have already been loaded" % len(vcf_sample_ids))
                return
        except ObjectDoesNotExist:
            pass

        if only_validate:
            return

        # TODO gsutil config, gcloud auth login

        # optionally add sample ids from the VCF to the project
        if len(vcf_sample_id_to_sample_record) < len(vcf_sample_ids):
            responded_yes = ask_yes_no_question("Add these %s extra VCF samples to %s?" % (
                len(vcf_sample_ids) - len(vcf_sample_id_to_sample_record),
                project.name
            ))
            if responded_yes:
                add_or_update_individuals_and_families(project, [
                    {'familyId': sample_id, 'individualId': sample_id}
                    for sample_id in (set(vcf_sample_ids) - set(vcf_sample_id_to_sample_record.keys()))
                ])

                vcf_sample_id_to_sample_record = _match_vcf_id_to_sample_id(
                    vcf_sample_ids,
                    project,
                    sample_type,
                    max_edit_distance=max_edit_distance,
                    only_validate=only_validate,
                )

        if len(vcf_sample_id_to_sample_record) == 0:
            logger.info("No matches found between the %s sample id(s) in the VCF and the %s %s sample id(s) in %s" % (
                len(vcf_sample_ids),
                len(Sample.objects.filter(individual__family__project=project, sample_type=sample_type))),
                sample_type,
                project_guid,
            )
            return

         # retrieve or create Dataset record and link it to sample(s)
        try:
            if dataset_id is None:
                dataset = Dataset.objects.get(
                    analysis_type=analysis_type,
                    source_file_path=vcf_path,
                    project=project,
                )
            else:
                dataset = Dataset.objects.get(
                    dataset_id=dataset_id,
                )

                dataset.analysis_type=analysis_type
                dataset.source_file_path = vcf_path
                dataset.project = project
                dataset.save()

        except ObjectDoesNotExist:
            logger.info("Creating %s dataset for %s" % (analysis_type, vcf_path))
            dataset = _create_dataset(analysis_type, vcf_path, project)

        # link the Dataset record to Samples found in this VCF
        for sample_id, sample in vcf_sample_id_to_sample_record.items():
            dataset.samples.add(sample)

        # load the VCF
        source_file_path = dataset.source_file_path
        source_filename = os.path.basename(dataset.source_file_path)
        genome_version = dataset.project.genome_version
        genome_version_label="GRCh%s" % genome_version

        dataset_directory = os.path.join(PROJECT_DATA_DIR, "%(genome_version_label)s/%(dataset_id)s" % locals())
        raw_vcf_path = "%(dataset_directory)s/%(source_filename)s" % locals()
        vep_annotated_vds_path = "%(dataset_directory)s/%(dataset_id)s.vep.vds" % locals()

        if not inputs_older_than_outputs([source_file_path], [raw_vcf_path], label="copy step: "):
            logger.info("copy step: copying %(source_file_path)s to %(raw_vcf_path)s" % locals())
            copy_file(source_file_path, raw_vcf_path)

        with HailRunner(dataset.dataset_id) as hail_runner:
            vds_file = os.path.join(vep_annotated_vds_path, "metadata.json.gz")  # stat only works on files, not directories
            if not inputs_older_than_outputs([raw_vcf_path], [vds_file], label="vep annotation step: "):
                logger.info("vep annotation step: annotating %(raw_vcf_path)s and outputing to %(vep_annotated_vds_path)s" % locals())
                hail_runner.run_vep(raw_vcf_path, vep_annotated_vds_path)

            logger.info("export to elasticsearch step: exporting %(vep_annotated_vds_path)s to elasticsearch" % locals())
            hail_runner.export_to_elasticsearch(vep_annotated_vds_path, dataset_id, analysis_type, genome_version)

        logger.info("done")


def _create_dataset(analysis_type, source_file_path, project, dataset_id=None):

    if dataset_id is None:
        # compute a dataset_id based on properties of the source file
        file_stats = get_file_stats(source_file_path)
        dataset_id = "_".join(map(str, [
            datetime.datetime.fromtimestamp(float(file_stats.ctime)).strftime('%Y%m%d'),
            os.path.basename(source_file_path).split(".")[0][:20],
            file_stats.size
        ]))

    dataset = Dataset.objects.create(
        dataset_id=dataset_id,
        analysis_type=analysis_type,
        source_file_path=source_file_path,
        project=project,
    )

    return dataset


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


def _match_vcf_id_to_sample_id(vcf_sample_ids, project, sample_type, only_validate=False, max_edit_distance=0):
    logger.info("%s sample IDs found in VCF: %s" % (len(vcf_sample_ids), ", ".join(vcf_sample_ids)))

    vcf_sample_ids_set = set(vcf_sample_ids)

    # populate a dictionary of sample_id to sample_record
    vcf_sample_id_to_sample_record = {}

    # step 1. check for any existing sample records with the given sample type and with a
    # sample id that exactly matches the vcf sample id
    existing_samples_of_this_type = {
        s.sample_id: s for s in Sample.objects.select_related('individual').filter(individual__family__project=project, sample_type=sample_type)
    }
    for vcf_sample_id in vcf_sample_ids_set:
        if vcf_sample_id in existing_samples_of_this_type:
            logger.info("   vcf id %s exactly matched existing sample id %s for individual %s" % (
                vcf_sample_id,
                vcf_sample_id,
                existing_samples_of_this_type[vcf_sample_id].individual
            ))
            existing_sample_record = existing_samples_of_this_type[vcf_sample_id]
            vcf_sample_id_to_sample_record[vcf_sample_id] = existing_sample_record

    # step 2. check for individuals with an individual id that exactly matches the vcf sample id
    remaining_vcf_sample_ids = vcf_sample_ids_set - set(vcf_sample_id_to_sample_record.keys())
    all_individuals = Individual.objects.filter(family__project=project)
    if len(remaining_vcf_sample_ids) > 0:
        for individual in all_individuals:
            if individual.individual_id in remaining_vcf_sample_ids:
                logger.info("   individual id %s exactly matched the VCF sample id" % (individual.individual_id, ))

                vcf_sample_id = individual.individual_id

                new_sample_record = "placeholder"
                if not only_validate:
                    new_sample_record = Sample.objects.create(sample_id=vcf_sample_id, sample_type=sample_type, individual=individual)
                vcf_sample_id_to_sample_record[vcf_sample_id] = new_sample_record

    # step 3. check if remaining vcf_sample_ids are similar to exactly one individual id
    remaining_vcf_sample_ids = vcf_sample_ids_set - set(vcf_sample_id_to_sample_record.keys())
    if len(remaining_vcf_sample_ids) > 0:
        individual_ids_with_matching_sample_record = set(sample.individual.individual_id for sample in vcf_sample_id_to_sample_record.values())
        individual_ids_without_matching_sample_record = set(individual.individual_id for individual in all_individuals) - individual_ids_with_matching_sample_record

        if max_edit_distance > 0 and remaining_vcf_sample_ids and individual_ids_without_matching_sample_record:
            for vcf_sample_id in remaining_vcf_sample_ids:

                current_lowest_edit_distance = max_edit_distance
                current_lowest_edit_distance_individuals = []
                for individual_id in individual_ids_without_matching_sample_record:
                    n = compute_edit_distance(vcf_sample_id, individual_id)
                    if n < current_lowest_edit_distance:
                        current_lowest_edit_distance = n
                        current_lowest_edit_distance_individual = [individual]
                    elif n == current_lowest_edit_distance:
                        current_lowest_edit_distance_individual.append(individual)

                if len(current_lowest_edit_distance_individuals) == 1:
                    logger.info("   individual id %s matched VCF sample id %s (edit distance: %d)" % (
                        individual.individual_id, vcf_sample_id, current_lowest_edit_distance))

                    if not only_validate:
                        new_sample_record = Sample.objects.create(sample_id=vcf_sample_id, sample_type=sample_type, individual=individual)
                        vcf_sample_id_to_sample_record[vcf_sample_id] = new_sample_record

                    individual_ids_without_matching_sample_record.remove(individual.individual_id)

                elif len(current_lowest_edit_distance_individuals) >= 1:
                    logger.info("No match: VCF sample id %s matched multiple individual ids %s" % (
                        vcf_sample_id, ", ".join(i.individual_id for i in current_lowest_edit_distance_individuals)))

    else:
        individual_ids_without_matching_sample_record = set()

    # print stats
    if len(vcf_sample_id_to_sample_record):
        logger.info("summary: %s sample IDs matched existing IDs in %s" % (len(vcf_sample_id_to_sample_record), project.name))
    remaining_vcf_sample_ids = vcf_sample_ids_set - set(vcf_sample_id_to_sample_record.keys())
    if len(remaining_vcf_sample_ids):
        logger.info("summary: %s sample IDs didn't match any existing IDs in %s" % (len(remaining_vcf_sample_ids), project.name))

    #num_individuals_with_data_in_this_vcf = len(all_individuals) - len(individual_ids_without_matching_sample_record)
    #if num_individuals_with_data_in_this_vcf:
    #    logger.info("Will load variants for %s out of %s individuals in %s" % (num_individuals_with_data_in_this_vcf, len(all_individuals), project.name))
    #else:
    #    logger.info("None of the sample ids in the VCF matched existing IDs in %s" % project.name)

    return vcf_sample_id_to_sample_record


def compute_edit_distance(source, target):
    """Compute the levenshtein edit distance between 2 strings.

    Code from https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python
    """

    if len(source) < len(target):
        return compute_edit_distance(target, source)

    # So now we have len(source) >= len(target).
    if len(target) == 0:
        return len(source)

    # We call tuple() to force strings to be used as sequences
    # ('c', 'a', 't', 's') - numpy uses them as values by default.
    source = np.array(tuple(source))
    target = np.array(tuple(target))

    # We use a dynamic programming algorithm, but with the
    # added optimization that we only need the last two rows
    # of the matrix.
    previous_row = np.arange(target.size + 1)
    for s in source:
        # Insertion (target grows longer than source):
        current_row = previous_row + 1

        # Substitution or matching:
        # Target and source items are aligned, and either
        # are different (cost of 1), or are the same (cost of 0).
        current_row[1:] = np.minimum(
            current_row[1:],
            np.add(previous_row[:-1], target != s))

        # Deletion (target grows shorter than source):
        current_row[1:] = np.minimum(
            current_row[1:],
            current_row[0:-1] + 1)

        previous_row = current_row

    return previous_row[-1]