import logging
import numpy as np
from seqr.models import Individual, Sample

logger = logging.Logger(__name__)


def match_sample_ids_to_sample_records(
        project,
        sample_ids,
        sample_type,
        max_edit_distance=0,
        create_records_for_new_sample_ids=False):

    sample_ids_set = set(sample_ids)

    # populate a dictionary of sample_id to sample_record
    sample_id_to_sample_record = {}

    # step 1. check for any existing sample records with the given sample type and with a
    # sample id that exactly matches the sample id of an existing Sample record
    existing_samples_of_this_type = {
        s.sample_id: s for s in Sample.objects.select_related('individual').filter(individual__family__project=project, sample_type=sample_type)
    }
    for sample_id in sample_ids_set:
        if sample_id in existing_samples_of_this_type:
            logger.info("   sample id %s exactly matched existing sample id %s for individual %s" % (
                sample_id,
                sample_id,
                existing_samples_of_this_type[sample_id].individual
            ))
            existing_sample_record = existing_samples_of_this_type[sample_id]
            sample_id_to_sample_record[sample_id] = existing_sample_record

    # step 2. check for individuals with an individual id that exactly matches the vcf sample id
    remaining_sample_ids = sample_ids_set - set(sample_id_to_sample_record.keys())
    all_individuals = Individual.objects.filter(family__project=project)
    if len(remaining_sample_ids) > 0:
        for individual in all_individuals:
            if individual.individual_id in remaining_sample_ids:
                logger.info("   individual id %s exactly matched the sample id %s" % (individual.individual_id, individual.individual_id))

                sample_id = individual.individual_id

                if create_records_for_new_sample_ids:
                    new_sample_record = Sample.objects.create(sample_id=sample_id, sample_type=sample_type, individual=individual)
                    sample_id_to_sample_record[sample_id] = new_sample_record
                else:
                    sample_id_to_sample_record[sample_id] = None

    # step 3. check if remaining sample_ids are similar to exactly one individual id
    remaining_sample_ids = sample_ids_set - set(sample_id_to_sample_record.keys())
    if len(remaining_sample_ids) > 0:
        individual_ids_with_matching_sample_record = set(sample.individual.individual_id for sample in sample_id_to_sample_record.values())
        individual_ids_without_matching_sample_record = set(individual.individual_id for individual in all_individuals) - individual_ids_with_matching_sample_record

        if max_edit_distance > 0 and remaining_sample_ids and individual_ids_without_matching_sample_record:
            for sample_id in remaining_sample_ids:

                current_lowest_edit_distance = max_edit_distance
                current_lowest_edit_distance_individuals = []
                for individual_id in individual_ids_without_matching_sample_record:
                    n = compute_edit_distance(sample_id, individual_id)
                    if n < current_lowest_edit_distance:
                        current_lowest_edit_distance = n
                        current_lowest_edit_distance_individual = [individual]
                    elif n == current_lowest_edit_distance:
                        current_lowest_edit_distance_individual.append(individual)

                if len(current_lowest_edit_distance_individuals) == 1:
                    logger.info("   individual id %s approximately matched sample id %s (edit distance: %d)" % (
                        individual.individual_id, sample_id, current_lowest_edit_distance))

                    if create_records_for_new_sample_ids:
                        new_sample_record = Sample.objects.create(sample_id=sample_id, sample_type=sample_type, individual=individual)
                        sample_id_to_sample_record[sample_id] = new_sample_record
                    else:
                        sample_id_to_sample_record[sample_id] = None

                    individual_ids_without_matching_sample_record.remove(individual.individual_id)

                elif len(current_lowest_edit_distance_individuals) >= 1:
                    logger.info("No match: sample id %s approximately matched multiple individual ids %s" % (
                        sample_id, ", ".join(i.individual_id for i in current_lowest_edit_distance_individuals)))

    else:
        individual_ids_without_matching_sample_record = set()

    # print stats
    if len(sample_id_to_sample_record):
        logger.info("summary: %s sample IDs matched existing IDs in %s" % (len(sample_id_to_sample_record), project.name))
    remaining_sample_ids = sample_ids_set - set(sample_id_to_sample_record.keys())
    if len(remaining_sample_ids):
        logger.info("summary: %s sample IDs didn't match any existing IDs in %s" % (len(remaining_sample_ids), project.name))

    #num_individuals_with_sample_id_matches = len(all_individuals) - len(individual_ids_without_matching_sample_record)
    #if num_individuals_with_sample_id_matches:
    #    logger.info("Will load variants for %s out of %s individuals in %s" % (num_individuals_with_sample_id_matches, len(all_individuals), project.name))
    #else:
    #    logger.info("None of the sample ids in the VCF matched existing IDs in %s" % project.name)

    if not create_records_for_new_sample_ids:
        # drop placeholder entries where sample_record is None
        sample_id_to_sample_record = {
            sample_id: sample_record for sample_id, sample_record in sample_id_to_sample_record.items() if sample_record is not None
        }

    return sample_id_to_sample_record


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


