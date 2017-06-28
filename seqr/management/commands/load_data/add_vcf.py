
# b38 - gs://gmkf_engle_callset/900Genomes_full.vcf.gz
# b38 - gs://vep-test/APY-001.vcf.bgz
# b37 - ? - gs://winters/v33.winters.vcf.bgz

# check loading status ( sample_batch_id )

# delete sample batch ( sample_batch_id )

import logging
import numpy as np
import os

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from scipy.io.arff.arffread import read_header

from reference_data.models import GENOME_BUILD_GRCh37, GENOME_BUILD_CHOICES
from seqr.models import Project, Individual, Sample, Dataset
from seqr.utils.gcloud_utils import does_file_exist, read_header

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Adds a VCF to the system and loads it"""

    def add_arguments(self, parser):
        parser.add_argument("-t", "--sample-type", choices=[k for k, v in Sample.SAMPLE_TYPE_CHOICES],
            help="Type of sequencing that was used to generate this data (eg. WES, WGS, ..)", required=True)
        parser.add_argument("-b", "--genome-build", help="Genome build 37 or 38", choices=[c[0] for c in GENOME_BUILD_CHOICES], required=True)
        parser.add_argument("--validate-only", action="store_true", help="Only validate the vcf, and don't load it or create any meta-data records.")
        parser.add_argument("--max-edit-distance-for-id-match", help="Specify an edit distance > 0 to allow for non-exact matches when matching VCF sample ids to individual ids.", type=int, default=0)
        parser.add_argument("project_id", help="Project to which this VCF should be added")
        parser.add_argument("vcf_path", help="Variant callset file path")

    def handle(self, *args, **options):

        analysis_type = Dataset.ANALYSIS_TYPE_VARIANT_CALLS

        # parse and validate args
        project_guid = options["project_id"]
        sample_type = options["sample_type"]
        genome_build = options["genome_build"]
        validate_only = options["validate_only"]
        max_edit_distance = options["max_edit_distance_for_id_match"]
        vcf_path = options["vcf_path"]

        # look up project id
        try:
            project = Project.object.get(guid=project_guid)
        except ObjectDoesNotExist:
            raise CommandError("Invalid project id: %(project_guid)s" % locals())

        if project.genome_build_id != genome_build:
            raise CommandError("Genome build %s doesn't match the project's genome build which is %s" % (genome_build, project.genome_build_id))

        # validate VCF and get sample ids
        vcf_sample_ids = _validate_vcf(vcf_path, sample_type=sample_type, genome_build=genome_build)

        # populate a dictionary of sample_id to sample_record
        vcf_sample_id_to_sample_record = {}

        vcf_sample_ids_without_matching_sample_record = set(vcf_sample_ids)

        #   1st check for any existing sample records with the given sample type and with a sample id that exactly matches the vcf sample id
        existing_samples_of_this_type = {
            s.sample_id: s for s in Sample.objects.select_related('individual').filter(individual__family__project=project, sample_type=sample_type)
        }
        for vcf_sample_id in vcf_sample_ids_without_matching_sample_record:
            if vcf_sample_id in existing_samples_of_this_type:
                logger.info("Match: vcf id %s exactly matched existing sample id" % (vcf_sample_id, ))
                existing_sample_record = existing_samples_of_this_type[vcf_sample_id]
                vcf_sample_id_to_sample_record[vcf_sample_id] = existing_sample_record

                vcf_sample_ids_without_matching_sample_record.remove(vcf_sample_id)

        #   2nd check for individuals with an individual id that exactly matches the vcf sample id
        if vcf_sample_ids_without_matching_sample_record:
            all_individuals = Individual.objects.filter(family__project=project)
            for individual in all_individuals:
                if individual.individual_id in vcf_sample_ids_without_matching_sample_record:
                    logger.info("Match: individual id %s exactly matched the VCF sample id" % (individual.individual_id, ))

                    vcf_sample_id = individual.individual_id

                    if not validate_only:
                        new_sample_record = Sample.objects.create(sample_id=vcf_sample_id, sample_type=sample_type, individual=individual)
                        vcf_sample_id_to_sample_record[vcf_sample_id] = new_sample_record

                    vcf_sample_ids_without_matching_sample_record.remove(vcf_sample_id)


        # 3rd check if remaining vcf_sample_ids are similar to exactly one individual id
        individual_ids_with_matching_sample_record = set(sample.individual.individual_id for sample in vcf_sample_id_to_sample_record.values())
        individual_ids_without_matching_sample_record = set(individual.individual_id for individual in all_individuals) - individual_ids_with_matching_sample_record

        if max_edit_distance > 0 and vcf_sample_ids_without_matching_sample_record and individual_ids_without_matching_sample_record:
            for vcf_sample_id in vcf_sample_ids_without_matching_sample_record:

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
                    logger.info("Match: individual id %s matched VCF sample id %s (edit distance: %d)" % (
                        individual.individual_id, vcf_sample_id, current_lowest_edit_distance))

                    if not validate_only:
                        new_sample_record = Sample.objects.create(sample_id=vcf_sample_id, sample_type=sample_type, individual=individual)
                        vcf_sample_id_to_sample_record[vcf_sample_id] = new_sample_record

                    individual_ids_without_matching_sample_record.remove(individual.individual_id)

                elif len(current_lowest_edit_distance_individuals) >= 1:
                    logger.info("No match: VCF sample id %s matched multiple individual ids %s" % (
                        vcf_sample_id, ", ".join(i.individual_id for i in current_lowest_edit_distance_individuals)))

        # print stats
        logger.info("%s out of %s VCF sample ids matched existing individuals in %s" % (len(vcf_sample_id_to_sample_record), project.name))
        if len(vcf_sample_ids_without_matching_sample_record):
            logger.info("%s VCF sample ids didn't match individuals in %s" % (len(vcf_sample_ids_without_matching_sample_record), project.name))
        if len(individual_ids_without_matching_sample_record):
            logger.info("%s individuals in %s don't have a sample in this VCF" % (len(individual_ids_without_matching_sample_record), project.name))

        # check if Dataset record already exists for this vcf in this project
        try:
            dataset = Dataset.objects.get(
                analysis_type=analysis_type,
                source_file_path=vcf_path,
                sample__individual__family__project=project)

            new_sample_ids = set(vcf_sample_id_to_sample_record.keys())
            existing_sample_ids = set([s.sample_id for s in dataset.samples.all()])
            if dataset.is_loaded and len(new_sample_ids - existing_sample_ids) == 0:
                logger.info("All %s samples in this VCF are already loaded" % len(new_sample_ids))
                return
        except ObjectDoesNotExist:
            # TODO remove previous Dataset record
            pass

        if validate_only:
            return

        # create Dataset record and link it to sample(s)
        dataset = Dataset.objects.create(
            analysis_type=analysis_type,
            source_file_path=vcf_path)

        for sample_id, sample in vcf_sample_id_to_sample_record.items():
            dataset.samples.add(sample)

        # load the data
        _load_dataset(dataset)


def _validate_vcf(vcf_path, sample_type=None, genome_build=None):
    if not vcf_path or not isinstance(vcf_path, str):
        raise CommandError("Invalid vcf_path arg: %(vcf_path)s" % locals())

    if vcf_path.startswith("gs://"):
        if not does_file_exist(vcf_path):
            raise ValueError("%(vcf_path)s not found" % locals())
        header = read_header(vcf_path)

    else:
        if not os.path.isfile(vcf_path):
            raise ValueError("%(vcf_path)s not found" % locals())

    # TODO check header, sample_type, genome_build

    #3. return info, warning, error - info: # of samples that will have data, error: couldn't parse


def _load_dataset(dataset):
    pass

    #0. record 'started loading' event
    #1. update Dataset loading status
    #2. queue loading on cluster (or create new cluster?)
    # - copy to seqr cloud drive
    # - generate VEP annotated version
    # - load into database
    # - mark all samples as loaded  in database
    # - if error - mark as error
    # - if no new datasets to load since 5 minutes ago, delete the cluster.
    #3. record 'finished loading' event
    print("loading dataset: " + str(dataset))


def compute_edit_distance(source, target):
    """Edit distance - code from https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python"""
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