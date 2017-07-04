
# b38 - gs://gmkf_engle_callset/900Genomes_full.vcf.gz
# b38 - gs://vep-test/APY-001.vcf.bgz
# b37 - ? - gs://winters/v33.winters.vcf.bgz

# python manage.py add_vcf -t WES -g 37 R0390_1000_genomes_demo  gs://seqr-hail/test-data/1kg.subset_10k.vcf.bgz
# python manage.py add_vcf -t WGS -g 38 R0396_engle_2_sample gs://vep-test/APY-001.vcf.bgz
# python manage.py add_vcf -t WGS -g 38 R0397_engle_900 gs://seqr-hail/datasets/GRCh38/900Genomes_full.vcf.gz


# check loading status ( sample_batch_id )

# delete sample batch ( sample_batch_id )

import datetime
import logging
import numpy as np
import os

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from reference_data.models import GENOME_VERSION_CHOICES
from seqr.models import Project, Individual, Sample, Dataset
from seqr.pipelines.gcloud_pipeline import GCloudVariantPipeline
from seqr.pipelines.pipeline_utils import get_local_or_gcloud_file_stats
from seqr.utils.gcloud_utils import does_gcloud_file_exist, read_gcloud_file_header
from seqr.utils.shell_utils import ask_yes_no_question
from seqr.views.apis.individual_api import add_or_update_individuals_and_families

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Adds a VCF to a project and loads the variants"""

    def add_arguments(self, parser):
        parser.add_argument("-t", "--sample-type", choices=[k for k, v in Sample.SAMPLE_TYPE_CHOICES],
            help="Type of sequencing that was used to generate this data", required=True)
        parser.add_argument("-g", "--genome-version", help="Genome version 37 or 38", choices=[c[0] for c in GENOME_VERSION_CHOICES], required=True)
        parser.add_argument("--only-validate", action="store_true", help="Only validate the vcf, and don't load it or create any meta-data records.")
        parser.add_argument("--max-edit-distance-for-id-match", help="Specify an edit distance > 0 to allow for non-exact matches between VCF sample ids and Individual ids.", type=int, default=0)
        parser.add_argument("-p", "--pedigree-file", help="(optional) Format: .fam, .xls. For convenience, a pedigree file can be specified to add individuals to the project and specify their relationships ahead of adding the VCF.")
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
        pedigree_file = options["pedigree_file"]
        project_guid = options["project_id"]
        vcf_path = options["vcf_path"]
        dataset_id = options["dataset_id"]

        # look up project id
        try:
            project = Project.objects.get(guid=project_guid)
        except ObjectDoesNotExist:
            raise CommandError("Invalid project id: %(project_guid)s" % locals())

        if project.genome_version != genome_version:
            raise CommandError("Genome version %s doesn't match the project's genome build which is %s" % (genome_version, project.genome_version))

        if pedigree_file and not os.path.isfile(pedigree_file):
            raise CommandError("Can't open pedigree file: %(pedigree_file)s" % locals())

        if pedigree_file:
            #parse_individuals()
            #add_or_update_individuals_and_families()
            raise CommandError("Pedigree file processing not yet implemented.")

        # validate VCF and get sample ids
        vcf_sample_ids = _validate_vcf(vcf_path, sample_type=sample_type, genome_version=genome_version)

        vcf_sample_id_to_sample_record = _match_vcf_id_to_sample_id(
            vcf_sample_ids,
            project,
            sample_type,
            max_edit_distance=max_edit_distance,
            only_validate=only_validate,
        )

        # check if Dataset record already exists for this vcf in this project
        try:
            dataset = Dataset.objects.get(id__in=
                Dataset.objects.filter(
                    analysis_type=analysis_type,
                    source_file_path=vcf_path,
                    project=project,
                ).values_list('id', flat=True)
            )

            vcf_sample_ids = set(vcf_sample_id_to_sample_record.keys())
            existing_sample_ids = set([s.sample_id for s in dataset.samples.all()])
            if dataset.is_loaded and len(vcf_sample_ids - existing_sample_ids) == 0:
                logger.info("All %s samples in this VCF are already loaded" % len(vcf_sample_ids))
                return
        except ObjectDoesNotExist:
            # TODO remove previous Dataset records?
            pass

        if only_validate:
            return

        # TODO gsutil config, gcloud auth login

        if len(vcf_sample_id_to_sample_record) < len(vcf_sample_ids):
            responded_yes = ask_yes_no_question("Add these %s extra VCF samples to %s?" % (len(vcf_sample_ids) - len(vcf_sample_id_to_sample_record), project.name))
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

        # retrieve or create Dataset record and link it to sample(s)
        if len(vcf_sample_id_to_sample_record) > 0:
            try:
                if dataset_id is None:
                    dataset = Dataset.objects.get(id__in=Dataset.objects.filter(
                        analysis_type=analysis_type,
                        source_file_path=vcf_path,
                        project=project,
                    ).values_list('id', flat=True))
                else:
                    dataset = Dataset.objects.get(id__in=Dataset.objects.filter(
                        dataset_id=dataset_id,
                    ).values_list('id', flat=True))

                    dataset.analysis_type=analysis_type
                    dataset.source_file_path = vcf_path
                    dataset.project = project
                    dataset.save()

            except ObjectDoesNotExist:
                logger.info("Creating %s dataset for %s" % (analysis_type, vcf_path))
                dataset = _create_dataset(analysis_type, vcf_path, project)

            # link the Dataset record to Sample records
            for sample_id, sample in vcf_sample_id_to_sample_record.items():
                dataset.samples.add(sample)

            # load the VCF
            p = GCloudVariantPipeline(dataset)
            p.run_pipeline()

        logger.info("done")


def _create_dataset(analysis_type, source_file_path, project, dataset_id=None):

    if dataset_id is None:
        # compute a dataset_id based on properties of the source file
        file_stats = get_local_or_gcloud_file_stats(source_file_path)
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

    if vcf_path.startswith("gs://"):
        if not does_gcloud_file_exist(vcf_path):
            raise ValueError("%(vcf_path)s not found" % locals())
        header_content = read_gcloud_file_header(vcf_path, header_prefix="#CHROM")
    else:
        if not os.path.isfile(vcf_path):
            raise ValueError("%(vcf_path)s not found" % locals())

    # TODO if annotating using gcloud, check whether dataproc has access to file

    # TODO check header, sample_type, genome_version
    header_fields = header_content.strip().split('\t')
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