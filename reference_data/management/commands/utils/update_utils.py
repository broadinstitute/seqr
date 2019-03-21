import logging
import os
from tqdm import tqdm
from django.core.management.base import BaseCommand, CommandError
from reference_data.management.commands.utils.download_utils import download_file
from reference_data.management.commands.utils.gene_utils import get_genes_by_symbol
from reference_data.models import GeneInfo

logger = logging.getLogger(__name__)


class ReferenceDataHandler(object):

    model_cls = None
    url = None
    header_fields = None
    post_process_models = None

    gene_reference = {'gene_symbols_to_gene': get_genes_by_symbol()}

    @staticmethod
    def parse_record(record):
        raise NotImplementedError

    @staticmethod
    def get_file_header(f):
        return next(f).rstrip('\n\r').split('\t')

    @classmethod
    def get_gene_for_record(cls, record):
        gene_symbols_to_gene = cls.gene_reference['gene_symbols_to_gene']
        gene_symbol = record.pop('gene_symbol')

        if not gene_symbols_to_gene.get(gene_symbol):
            raise ValueError('Gene "{}" not found in the GeneInfo table'.format(gene_symbol))

        return gene_symbols_to_gene[gene_symbol]


class GeneCommand(BaseCommand):
    reference_data_handler = None

    def add_arguments(self, parser):
        parser.add_argument('file_path', nargs="?",
                            help="local path of primate ai file",
                            default=os.path.join('resource_bundle', os.path.basename(self.reference_data_handler.url)))

    def handle(self, *args, **options):
        if GeneInfo.objects.count() == 0:
            raise CommandError("GeneInfo table is empty. Run './manage.py update_gencode' before running this command.")

        update_records(self.reference_data_handler, file_path=options.get('file_path'), )


def update_records(reference_data_handler, file_path=None):
    """
    Args:
        file_path (str): optional local file path. If not specified, or the path doesn't exist, the table will be downloaded.
    """

    if not file_path or not os.path.isfile(file_path):
        if not reference_data_handler.url:
            raise CommandError('Either file path or url is required')
        file_path = download_file(reference_data_handler.url)

    model_cls = reference_data_handler.model_cls
    model_name = model_cls.__name__
    model_objects = getattr(model_cls, 'objects')

    logger.info("Deleting {} existing {} records".format(model_objects.count(), model_name))
    model_objects.all().delete()

    models = []
    skip_counter = 0
    logger.info('Parsing file')
    with open(file_path) as f:
        header_fields = reference_data_handler.get_file_header(f)

        for line in tqdm(f, unit=" records"):
            record = dict(zip(header_fields, line.rstrip('\r\n').split('\t')))
            for record in reference_data_handler.parse_record(record):
                if record is None:
                    continue

                try:
                    record['gene'] = reference_data_handler.get_gene_for_record(record)
                except ValueError as e:
                    skip_counter += 1
                    logger.debug(e)
                    continue

                models.append(model_cls(**record))

    if reference_data_handler.post_process_models:
        reference_data_handler.post_process_models(models)

    logger.info("Creating {} {} records".format(len(models), model_name))
    model_objects.bulk_create(models)

    logger.info("Done")
    logger.info("Loaded {} {} records from {}. Skipped {} records with unrecognized genes.".format(
        model_objects.count(), model_name, file_path, skip_counter))
    if skip_counter > 0:
        logger.info('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
