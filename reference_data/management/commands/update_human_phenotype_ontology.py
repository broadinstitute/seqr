import logging
import requests
from tqdm import tqdm

from django.db import transaction
from django.core.management.base import BaseCommand

from reference_data.models import HumanPhenotypeOntology

logger = logging.getLogger(__name__)


def parse_obo_file(file_iterator):
    """
    Parse an .obo file which contains a record for each term in the Human Phenotype Ontology

    Args:
        file_iterator: Iterator over lines in the hp.obo file
    Returns:
        dictionary that maps HPO id strings to a record containing
    """

    hpo_id_to_record = {}
    for line in tqdm(file_iterator, unit=" lines"):
        line = line.strip("\n")
        if line.startswith("id: "):
            hpo_id = line.split("id: ")[1]
            hpo_id_to_record[hpo_id] = {
                'hpo_id': hpo_id,
                'is_category': False,
                #'definition': None,
                #'comment': None,
            }
        elif line.startswith("is_a: "):
            is_a = line.split(" ")[1]
            if is_a == "HP:0000118":
                hpo_id_to_record[hpo_id]['is_category'] = True

            hpo_id_to_record[hpo_id]['parent_id'] = is_a
        elif line.startswith("name: "):
            name = line.split(" ")[1]
            hpo_id_to_record[hpo_id]['name'] = name
        elif line.startswith("def: "):
            definition = line.split(" ")[1]
            hpo_id_to_record[hpo_id]['definition'] = definition
        elif line.startswith("comment: "):
            comment = line.split(" ")[1]
            hpo_id_to_record[hpo_id]['comment'] = comment

    return hpo_id_to_record


def get_category_id(hpo_id_to_record, hpo_id):
    """For a given hpo_id, get the hpo id of it's top-level category (eg. 'cardiovascular') and
    return it. If the hpo_id belongs to multiple top-level categories, return one of them.
    """

    if hpo_id == "HP:0000001":
        return None

    if 'parent_id' not in hpo_id_to_record[hpo_id]:
        return None

    while hpo_id_to_record[hpo_id]['parent_id'] != "HP:0000118":

        hpo_id = hpo_id_to_record[hpo_id]['parent_id']
        if hpo_id == "HP:0000001":
            return None
        if hpo_id not in hpo_id_to_record:
            raise ValueError("Strange id: %s" % hpo_id)

    return hpo_id


class Command(BaseCommand):
    """Command to download the latest hp.obo release and update the HumanPhenotypeOntology table."""

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):

        url = 'http://purl.obolibrary.org/obo/hp.obo'
        print("Parsing %s" % url)
        response = requests.get(url)
        obo_file_iterator = response.content.split("\n")

        hpo_id_to_record = parse_obo_file(obo_file_iterator)

        # for each hpo id, find its top level category
        for hpo_id in hpo_id_to_record.keys():
            hpo_id_to_record[hpo_id]['category_id'] = get_category_id(hpo_id_to_record, hpo_id)

        # save to database
        records_in_category = [
            record for record in hpo_id_to_record.values() if record['category_id'] is not None
        ]

        logger.info("Deleting table with %s records and creating new table with %s records" % (
            HumanPhenotypeOntology.objects.all().count(),
            len(records_in_category))
        )

        with transaction.atomic():
            HumanPhenotypeOntology.objects.all().delete()

            HumanPhenotypeOntology.objects.bulk_create(
                HumanPhenotypeOntology(**record) for record in tqdm(records_in_category, unit=" records"),
            )

        logger.info("Done")