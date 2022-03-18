import csv
import logging
from tqdm import tqdm

from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GenCC

logger = logging.getLogger(__name__)

CLASSIFICATION_FIELDS = {
    'disease_title': 'disease',
    'classification_title': 'classification',
    'moi_title': 'moi',
    'submitter_title': 'submitter',
    'submitted_as_date': 'date',
}

class GenCCReferenceDataHandler(ReferenceDataHandler):

    model_cls = GenCC
    url = 'https://search.thegencc.org/download/action/submissions-export-csv'

    @staticmethod
    def get_file_header(f):
        return [k.replace('"', '') for k in next(f).rstrip('\n\r').split(',')]

    @staticmethod
    def get_file_iterator(f):
        return super(GenCCReferenceDataHandler, GenCCReferenceDataHandler).get_file_iterator(csv.reader(f))

    @staticmethod
    def parse_record(record):
        yield {
            'gene_symbol': record['gene_symbol'],
            'hgnc_id': record['gene_curie'],
            'classifications': [{title: record[field] for field, title in CLASSIFICATION_FIELDS.items()}]
        }

    @staticmethod
    def post_process_models(models):
        #  Group all classifications for a gene into a single model
        models_by_gene = {}
        for model in tqdm(models, unit=' models'):
            if model.gene in models_by_gene:
                models_by_gene[model.gene].classifications += model.classifications
            else:
                models_by_gene[model.gene] = model

        models.clear()
        models.extend(models_by_gene.values())


class Command(GeneCommand):
    reference_data_handler = GenCCReferenceDataHandler
