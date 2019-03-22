import logging
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler, update_records
from reference_data.models import MGI, dbNSFPGene

logger = logging.getLogger(__name__)


class MGIReferenceDataHandler(ReferenceDataHandler):

    model_cls = MGI
    url = "http://www.informatics.jax.org/downloads/reports/HMD_HumanPhenotype.rpt"

    entrez_id_to_gene = {
        dbnsfp.entrez_gene_id: dbnsfp.gene for dbnsfp in dbNSFPGene.objects.all().prefetch_related('gene')
    }

    @staticmethod
    def get_file_header(f):
        return ['gene_symbol', 'entrez_gene_id', 'homologene_id', '?', 'mouse_gene_symbol', 'marker_id', 'phenotype_ids']

    @staticmethod
    def parse_record(record):
        yield {k: v.strip() for k, v in record.items() if k in ['gene_symbol', 'marker_id', 'entrez_gene_id']}

    @classmethod
    def get_gene_for_record(cls, record):
        gene = cls.entrez_id_to_gene.get(record.pop('entrez_gene_id'))
        if gene:
            del record['gene_symbol']
            return gene

        return super(MGIReferenceDataHandler, cls).get_gene_for_record(record)


class Command(GeneCommand):
    reference_data_handler = MGIReferenceDataHandler


def update_mgi(**kwargs):
    """
    Args:
        file_path (str): optional local file path. If not specified, or the path doesn't exist, the table will be downloaded.
    """
    update_records(MGIReferenceDataHandler, **kwargs)
