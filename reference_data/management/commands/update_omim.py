import logging
import os
from tqdm import tqdm
import urllib

from django.core.management.base import BaseCommand

from reference_data.pipelines.generate_omim_tsv import parse_genemap2_table
from reference_data.models import OMIM

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration", default=os.environ.get("OMIM_KEY"))

    def handle(self, *args, **options):
        omim_key = options['omim_key']
        url = "http://data.omim.org/downloads/%(omim_key)s/genemap2.txt" % locals()
        logger.info("Downloading genemap2.txt file...")
        logger.info("URL: " + url)
        genemap2_file = tqdm(urllib.urlopen(url), unit=" lines")
        genemap2_records = parse_genemap2_table(genemap2_file)

        omim_records = [OMIM(**record) for record in genemap2_records]
        logger.info("Inserting %s records into OMIM table" % len(omim_records))
        OMIM.objects.all().delete()
        OMIM.objects.bulk_create(tqdm(omim_records, unit=" records"))

        logger.info("Done")
