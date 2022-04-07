import logging
from django.core.management.base import CommandError

from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import MGI, dbNSFPGene

logger = logging.getLogger(__name__)


class MGIReferenceDataHandler(ReferenceDataHandler):

    model_cls = MGI
    url = "https://storage.googleapis.com/seqr-reference-data/mgi/HMD_HumanPhenotype.rpt.txt"

    def __init__(self, **kwargs):
        if dbNSFPGene.objects.count() == 0:
            raise CommandError("dbNSFPGene table is empty. Run './manage.py update_dbnsfp_gene' before running this command.")
        self.entrez_id_to_gene = {
            dbnsfp.entrez_gene_id: dbnsfp.gene for dbnsfp in dbNSFPGene.objects.all().prefetch_related('gene')
        }
        super(MGIReferenceDataHandler, self).__init__(**kwargs)

    @staticmethod
    def get_file_header(f):
        return ['gene_symbol', 'entrez_gene_id', 'mouse_gene_symbol', 'marker_id', 'phenotype_ids']

    @staticmethod
    def parse_record(record):
        yield {k: v.strip() for k, v in record.items() if k in ['gene_symbol', 'marker_id', 'entrez_gene_id']}

    def get_gene_for_record(self, record):
        entrez_gene = self.entrez_id_to_gene.get(record.pop('entrez_gene_id'))

        try:
            return super(MGIReferenceDataHandler, self).get_gene_for_record(record)
        except ValueError as e:
            if entrez_gene:
                return entrez_gene
            raise e

class Command(GeneCommand):
    reference_data_handler = MGIReferenceDataHandler
