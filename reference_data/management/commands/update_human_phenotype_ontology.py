import logging
import os
from tqdm import tqdm

from django.db import transaction
from django.core.management.base import BaseCommand

from reference_data.management.commands.utils.download_utils import download_file
from reference_data.models import HumanPhenotypeOntology

logger = logging.getLogger(__name__)


HP_OBO_URL = 'http://purl.obolibrary.org/obo/hp.obo'


class Command(BaseCommand):
    help = "Downloads the latest hp.obo release and update the HumanPhenotypeOntology table"

    def add_arguments(self, parser):
        parser.add_argument('hpo_file_path', help="optional hp.obo file path. If not specified, the file will be downloaded.", nargs='?')

    def handle(self, *args, **options):
        update_hpo(hpo_file_path=options["hpo_file_path"])


def update_hpo(hpo_file_path=None):
    """
    Args:
        hpo_file_path (str): optional local hp.obo file path. If not specified, or the path doesn't exist, the file
            will be downloaded.
    """

    if not hpo_file_path or not os.path.isfile(hpo_file_path):
        hpo_file_path = download_file(url=HP_OBO_URL)

    with open(hpo_file_path) as f:
        print("Parsing {}".format(HP_OBO_URL))
        hpo_id_to_record = parse_obo_file(f)

    # for each hpo id, find its top level category
    for hpo_id in hpo_id_to_record.keys():
        hpo_id_to_record[hpo_id]['category_id'] = get_category_id(hpo_id_to_record, hpo_id)

    # save to database
    records_in_category = [
        record for record in hpo_id_to_record.values() if record['category_id'] is not None
    ]

    logger.info("Deleting HumanPhenotypeOntology table with %s records and creating new table with %s records" % (
        HumanPhenotypeOntology.objects.all().count(),
        len(records_in_category)))

    with transaction.atomic():
        HumanPhenotypeOntology.objects.all().delete()

        HumanPhenotypeOntology.objects.bulk_create(
            HumanPhenotypeOntology(**record) for record in tqdm(records_in_category, unit=" records"))

    logger.info("Done")


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
        line = line.rstrip("\n")
        value = " ".join(line.split(" ")[1:])
        if line.startswith("id: "):
            hpo_id = value
            hpo_id_to_record[hpo_id] = {
                'hpo_id': hpo_id,
                'is_category': False,
            }
        elif line.startswith("is_a: "):
            is_a = value.split(" ! ")[0]
            if is_a == "HP:0000118":
                hpo_id_to_record[hpo_id]['is_category'] = True
            hpo_id_to_record[hpo_id]['parent_id'] = is_a
        elif line.startswith("name: "):
            hpo_id_to_record[hpo_id]['name'] = value
        elif line.startswith("def: "):
            hpo_id_to_record[hpo_id]['definition'] = value
        elif line.startswith("comment: "):
            hpo_id_to_record[hpo_id]['comment'] = value

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

