import csv
import logging

from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import ClinGen

logger = logging.getLogger(__name__)


class ClinGenReferenceDataHandler(ReferenceDataHandler):

    model_cls = ClinGen
    url = 'https://search.clinicalgenome.org/kb/gene-dosage/download'

    @staticmethod
    def get_file_header(f):
        csv_f = csv.reader(f)
        next(row for row in csv_f if all(ch == '+' for ch in row[0])) # iterate past the metadata info
        header_line = next(csv_f)
        next(csv_f) # there is another padding row before the content starts

        return [col.replace(' ', '_').lower() for col in header_line]

    @staticmethod
    def get_file_iterator(f):
        return super(ClinGenReferenceDataHandler, ClinGenReferenceDataHandler).get_file_iterator(csv.reader(f))

    @staticmethod
    def parse_record(record):
        yield {
            'gene_symbol': record['gene_symbol'],
            'haploinsufficiency': record['haploinsufficiency'].replace(' for Haploinsufficiency', ''),
            'triplosensitivity': record['triplosensitivity'].replace(' for Triplosensitivity', ''),
            'href': record['online_report'],
        }


class Command(GeneCommand):
    reference_data_handler = ClinGenReferenceDataHandler
