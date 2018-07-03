import logging
import numpy as np
from django.utils import timezone
from django.db.models.query_utils import Q

from seqr.models import Individual, Sample

logger = logging.getLogger(__name__)


def match_sample_ids_to_sample_records(
        project,
        sample_ids,
        sample_type,
        dataset_type,
        elasticsearch_index,
        max_edit_distance=0,
        create_sample_records=False):
    """Goes through the given list of sample_ids and finds existing Sample records of the given
    sample_type with ids from the list. For sample_ids that aren't found to have existing Sample
    records, it looks for Individual records that have an individual_id that either exactly or
    approximately equals one of the sample_ids in the list and optionally creates new Sample
    records for these.

    Args:
        project (object): Django ORM project model
        sample_ids (list): a list of sample ids for which to find matching Sample records
        sample_type (string): one of the Sample.SAMPLE_TYPE_* constants
        max_edit_distance (int): max permitted edit distance for approximate matches
        create_sample_records (bool): whether to create new Sample records for sample_ids that
            don't match existing Sample records, but do match individual_id's of existing
            Individual records.

    Returns:
        dict: sample_id_to_sample_record containing the matching Sample records (including any
            newly-created ones)
    """

    sample_id_to_sample_record = find_matching_sample_records(project, sample_ids, sample_type, dataset_type, elasticsearch_index)
    logger.info(str(len(sample_id_to_sample_record)) + " exact sample record matches")

    remaining_sample_ids = set(sample_ids) - set(sample_id_to_sample_record.keys())
    created_sample_ids = []
    if len(remaining_sample_ids) > 0:
        already_matched_individual_ids = {
            sample.individual.individual_id for sample in sample_id_to_sample_record.values()
        }

        remaining_individuals_dict = {
            i.individual_id: i for i in Individual.objects.filter(family__project=project)
            if i.individual_id not in already_matched_individual_ids
        }

        # find Individual records with exactly-matching individual_ids
        sample_id_to_individual_record = {}
        for sample_id in remaining_sample_ids:
            if sample_id not in remaining_individuals_dict:
                continue
            sample_id_to_individual_record[sample_id] = remaining_individuals_dict[sample_id]
            del remaining_individuals_dict[sample_id]

        logger.info(str(len(sample_id_to_individual_record)) + " matched individual ids")
        remaining_sample_ids = remaining_sample_ids - set(sample_id_to_individual_record.keys())

        # find approximately-matching individual ids
        if len(remaining_sample_ids) > 0:
            sample_id_to_approximately_matching_individual_records = _find_approximate_match_individual_records(
                remaining_sample_ids, remaining_individuals_dict, max_edit_distance)

            logger.info(str(len(sample_id_to_approximately_matching_individual_records)) + " approximately matched individual ids")
            sample_id_to_individual_record.update(sample_id_to_approximately_matching_individual_records)

        # create new Sample records for Individual records that matches
        if create_sample_records:
            created_sample_ids = sample_id_to_individual_record.keys()
            for sample_id, individual in sample_id_to_individual_record.items():
                new_sample = Sample.objects.create(
                    sample_id=sample_id,
                    sample_type=sample_type,
                    dataset_type=dataset_type,
                    elasticsearch_index=elasticsearch_index,
                    individual=individual,
                    sample_status=Sample.SAMPLE_STATUS_LOADED,
                    loaded_date=timezone.now(),
                )
                sample_id_to_sample_record[sample_id] = new_sample

    return sample_id_to_sample_record, created_sample_ids


def find_matching_sample_records(project, sample_ids, sample_type, dataset_type, elasticsearch_index):
    """Find and return Samples of the given sample_type whose sample ids are in sample_ids list

    Args:
        project (object): Django ORM project model
        sample_ids (list): a list of sample ids for which to find matching Sample records
        sample_type (string): one of the Sample.SAMPLE_TYPE_* constants

    Returns:
        dict: sample_id_to_sample_record containing the matching Sample records
    """

    if len(sample_ids) == 0:
        return {}

    sample_id_to_sample_record = {}
    for sample in Sample.objects.select_related('individual').filter(Q(
        individual__family__project=project,
        sample_type=sample_type,
        dataset_type=dataset_type,
        sample_id__in=sample_ids),
        Q(elasticsearch_index=elasticsearch_index) | Q(elasticsearch_index__isnull=True)
    ):

        sample_id_to_sample_record[sample.sample_id] = sample

    return sample_id_to_sample_record


def find_matching_individuals(
    project,
    sample_ids,
    max_edit_distance=0,
    individual_ids_to_exclude=None
):
    """Looks for Individual records that have an individual_id that either exactly or
    approximately matches one of the sample_ids in the list.

    Args:
        project (object): Django ORM project model
        sample_ids (list): a list of sample ids for which to find matching Sample records
        max_edit_distance (int): max permitted edit distance for approximate matches
        individual_ids_to_exclude (list): don't match against individuals with ids in this list

    Returns:
        dict: maps sample_id to the matching Individual record for all sample_ids that had a match
    """

    exclude_individual_ids = set(individual_ids_to_exclude or [])

    individuals_dict = {
        i.individual_id: i for i in Individual.objects.filter(family__project=project)
        if i.individual_id not in exclude_individual_ids
    }

    # find Individual records with exactly-matching individual_ids
    sample_id_to_individual_record = {}
    for sample_id in sample_ids:
        if sample_id not in individuals_dict:
            continue

        sample_id_to_individual_record[sample_id] = individuals_dict[sample_id]
        del individuals_dict[sample_id]  # exclude matched individuals from approximate matching

    remaining_sample_ids = set(sample_ids) - set(sample_id_to_individual_record.keys())

    # find Individual records with approximately-matching individual_ids
    if len(remaining_sample_ids) > 0:
        sample_id_to_individual_record.update(
            _find_approximate_match_individual_records(
                remaining_sample_ids,
                individuals_dict,
                max_edit_distance)
        )

    return sample_id_to_individual_record


def _find_approximate_match_individual_records(
    sample_ids_set,
    individual_records_dict,
    max_edit_distance,
):
    """Find Individual records in the given project whose individual_ids approximately match ids in
    the given sample_ids_set, as constrained by the max_edit_distance.

    Args:
        sample_ids_set (set): sample ids for which to look for matches
        individual_records_dict (dict): maps individual_id to individual ORM record object. This
            method will look for matches to these individual ids.
        max_edit_distance (int): see #_compute_edit_distance

    Returns:
        dict: mapping of sample_id to Individual records that matched.
    """
    if not sample_ids_set or not individual_records_dict:
        return {}

    sample_id_to_individual_record = {}
    for sample_id in sample_ids_set:
        try:
            sample_id, individual = _find_individual_id_with_lowest_edit_distance(
                sample_id, individual_records_dict, max_edit_distance)
            sample_id_to_individual_record[sample_id] = individual
        except ValueError as e:
            logger.error(e)
            continue

    return sample_id_to_individual_record


def _find_individual_id_with_lowest_edit_distance(
    sample_id,
    individual_records_dict,
    max_edit_distance=0,
    case_sensitive=False,
):
    """Compares the given sample_id to all keys in individual_records_dict and, if there's a match,
    returns the matching key and value from individual_records_dict.

    For an individual id to be considered matching, it must have:
        - no more than max_edit_distance mismatches with sample_id
        - all other individual_ids in the project must have more mismatches with the sample_id, so
            that the match is unambiguous

    Args:
        sample_id (string): sample id to match
        individual_records_dict (dict): individual ids mapped to individual records. This method
            will look for matches against the keys of this dictinoary.
        max_edit_distance (int): max permitted edit distance between the sample id and an
            individual id for the 2 to be considered a match
        case_sensitive (bool): whether to count upper vs. lower case as a mismatch
    Return:
        2-tuple: (sample_id, individual) representing the matching sample_id and Individual object

    Raises:
        ValueError: if no matches found, or multiple matches found with identical edit distance
    """
    current_lowest_edit_distance_individuals = []

    if not case_sensitive:
        sample_id = sample_id.lower()

    for individual_id, individual in individual_records_dict.items():
        if not case_sensitive:
            individual_id = individual_id.lower()

        n = _compute_edit_distance(sample_id, individual_id)
        if n < max_edit_distance:
            max_edit_distance = n
            current_lowest_edit_distance_individuals = [individual]
        elif n == max_edit_distance:
            current_lowest_edit_distance_individuals.append(individual)

    if len(current_lowest_edit_distance_individuals) == 1:
        logger.info("   Individual id %s approximately matched sample id %s (edit distance: %d)" % (
            individual.individual_id, sample_id, max_edit_distance))

        individual = current_lowest_edit_distance_individuals[0]
        return individual.individual_id, individual

    if len(current_lowest_edit_distance_individuals) >= 1:
        raise ValueError(("Too many matches: sample id %s approximately matched multiple individual"
            " ids: %s (edit_distance: %d)") % (
                sample_id,
                ", ".join(i.individual_id for i in current_lowest_edit_distance_individuals),
                max_edit_distance
            ))
    else:
        raise ValueError(
            "No matches: sample id %s didn't match any individual ids (max edit distance: %s)" % (
            sample_id, max_edit_distance))


def _compute_edit_distance(source, target):
    """Code for computing the levenshtein edit distance from
    https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python

    Args:
        source (string): string1
        target (string): string2

    Return:
        int: levenshtein edit distance
    """

    if len(source) < len(target):
        return _compute_edit_distance(target, source)

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
