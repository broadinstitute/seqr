import logging
import os
from tqdm import tqdm
from django.core.management.base import BaseCommand, CommandError
from reference_data.management.commands.utils.download_utils import download_file
from reference_data.models import TranscriptInfo, GeneConstraint

logger = logging.getLogger(__name__)

GENE_CONSTRAINT_SCORES_URL = "http://storage.googleapis.com/seqr-reference-data/gene_constraint/gnomad.v2.1.1.lof_metrics.by_gene.txt"


class Command(BaseCommand):
    help = "Loads gene constraint data"

    def add_arguments(self, parser):
        parser.add_argument('gene_constraint_path', nargs="?",
            help="local path of gene constraint file",
            default=os.path.join('resource_bundle', os.path.basename(GENE_CONSTRAINT_SCORES_URL)))

    def handle(self, *args, **options):
        update_gene_constraint(gene_constraint_path=options.get('gene_constraint_path'))


def update_gene_constraint(gene_constraint_path=None):
    """
    Args:
        gene_constraint_path (str): optional local constraint table path. If not specified, or the path doesn't exist,
            the table will be downloaded.
    """
    if TranscriptInfo.objects.count() == 0:
        raise CommandError("TranscriptInfo table is empty. Run './manage.py update_gencode' before running this command.")

    if not gene_constraint_path or not os.path.isfile(gene_constraint_path):
        gene_constraint_path = download_file(GENE_CONSTRAINT_SCORES_URL)

    logger.info("Deleting {} existing GeneConstraint records".format(GeneConstraint.objects.count()))
    GeneConstraint.objects.all().delete()

    constraint_records = parse_gene_constraint_table(gene_constraint_path)

    # add _rank fields
    for field in ['mis_z', 'pLI']:
        for i, record in enumerate(sorted(constraint_records, key=lambda record: -1*record[field])):
            record['{}_rank'.format(field)] = i

    logger.info("Creating {} GeneConstraint records".format(len(constraint_records)))
    skip_counter = 0
    models = []

    transcripts_by_id = {t.transcript_id: t for t in TranscriptInfo.objects.all().prefetch_related('gene')}

    for record in tqdm(constraint_records, unit=" records"):
        transcript_id = record.pop("transcript_id")
        transcript = transcripts_by_id.get(transcript_id)
        if not transcript:
            skip_counter += 1
            logger.warn(("transcript id '{}' not found in TranscriptInfo table. "
                         "Running ./manage.py update_gencode to update the gencode version might fix this. "
                         "Full record: {}").format(transcript_id, record))
            continue

        record['gene'] = transcript.gene
        models.append(GeneConstraint(**record))

    GeneConstraint.objects.bulk_create(models)

    logger.info("Done")
    logger.info("Loaded {} GeneConstraint records from {}. Skipped {} records with unrecognized transcript id.".format(
        GeneConstraint.objects.count(), gene_constraint_path, skip_counter))


def parse_gene_constraint_table(gene_constraint_path):
    """Parse the genemap2 table, and yield a dictionary representing each gene-phenotype pair."""

    with open(gene_constraint_path) as f:
        header_fields = next(f).rstrip('\n\r').split('\t')

        constraint_records = []
        for line in f:
            record = dict(zip(header_fields, line.rstrip('\r\n').split('\t')))
            constraint_records.append({
                'transcript_id': record['transcript'].split(".")[0],
                'mis_z': float(record['mis_z']),
                'pLI': float(record['pLI']) if record['pLI'] != 'NA' else 0,
            })

        return constraint_records
