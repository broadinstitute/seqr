import logging
import os
from tqdm import tqdm
from django.core.management.base import BaseCommand
from reference_data.management.commands.utils.download_utils import download_file
from reference_data.management.commands.utils.gene_utils import get_genes_by_symbol
from reference_data.models import PrimateAI

logger = logging.getLogger(__name__)

PRIMATE_AI_GENES_URL = "http://storage.googleapis.com/seqr-reference-data/primate_ai/Gene_metrics_clinvar_pcnt.cleaned_v0.2.txt"


class Command(BaseCommand):
    help = "Loads Primate AI gene-level data"

    def add_arguments(self, parser):
        parser.add_argument('file_path', nargs="?",
                            help="local path of primate ai file",
                            default=os.path.join('resource_bundle', os.path.basename(PRIMATE_AI_GENES_URL)))

    def handle(self, *args, **options):
        update_primate_ai(file_path=options.get('file_path'))


def update_primate_ai(file_path=None):
    """
    Args:
        file_path (str): optional local file path. If not specified, or the path doesn't exist, the table will be downloaded.
    """

    if not file_path or not os.path.isfile(file_path):
        file_path = download_file(PRIMATE_AI_GENES_URL)

    logger.info("Deleting {} existing PrimateAI records".format(PrimateAI.objects.count()))
    PrimateAI.objects.all().delete()

    gene_symbols_to_gene = get_genes_by_symbol()

    models = []
    skip_counter = 0
    with open(file_path) as f:
        header_fields = next(f).rstrip('\n\r').split('\t')

        for line in tqdm(f, unit=" records"):
            record = dict(zip(header_fields, line.rstrip('\r\n').split('\t')))
            gene_symbol = record['genesymbol']

            if not gene_symbols_to_gene.get(gene_symbol):
                skip_counter += 1
                logger.warn('Gene "{}" not found in the GeneInfo table. Running ./manage.py update_gencode to update the gencode version might fix this.'.format(gene_symbol))
                continue

            models.append(PrimateAI(
                gene=gene_symbols_to_gene[gene_symbol],
                percentile_25=float(record['pcnt25']),
                percentile_75=float(record['pcnt75']),
            ))

    logger.info("Creating {} PrimateAI records".format(len(models)))
    PrimateAI.objects.bulk_create(models)

    logger.info("Done")
    logger.info("Loaded {} PrimateAI records from {}. Skipped {} records with unrecognized gene symbols.".format(
        PrimateAI.objects.count(), file_path, skip_counter))
