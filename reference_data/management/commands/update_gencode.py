import logging

from django.core.management.base import BaseCommand

from reference_data.management.commands.utils.gencode_utils import load_gencode_records, create_transcript_info, \
    LATEST_GENCODE_RELEASE
from reference_data.models import GeneInfo, TranscriptInfo, GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Loads the GRCh37 and/or GRCh38 versions of the Gencode GTF from a particular Gencode release"

    def add_arguments(self, parser):
        parser.add_argument('--reset', help="First drop any existing records from GeneInfo and TranscriptInfo", action="store_true")
        parser.add_argument('--gencode-release', help="gencode release number (eg. 28)", type=int, required=True, choices=range(19, LATEST_GENCODE_RELEASE+1))
        parser.add_argument('gencode_gtf_path', nargs="?", help="(optional) gencode GTF file path. If not specified, it will be downloaded.")
        parser.add_argument('genome_version', nargs="?", help="gencode GTF file genome version", choices=[GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38])

    def handle(self, *args, **options):

        update_gencode(
            gencode_release=options['gencode_release'],
            gencode_gtf_path=options.get('gencode_gtf_path'),
            genome_version=options.get('genome_version'),
            reset=options['reset'])


def update_gencode(gencode_release, gencode_gtf_path=None, genome_version=None, reset=False):
    """Update GeneInfo and TranscriptInfo tables.

    Args:
        gencode_release (int): the gencode release to load (eg. 25)
        gencode_gtf_path (str): optional local file path of gencode GTF file. If not provided, it will be downloaded.
        genome_version (str): '37' or '38'. Required only if gencode_gtf_path is specified.
        reset (bool): If True, all records will be deleted from GeneInfo and TranscriptInfo before loading the new data.
            Setting this to False can be useful to sequentially load more than one gencode release so that data in the
            tables represents the union of multiple gencode releases.
    """
    if reset:
        logger.info("Dropping the {} existing TranscriptInfo entries".format(TranscriptInfo.objects.count()))
        TranscriptInfo.objects.all().delete()
        logger.info("Dropping the {} existing GeneInfo entries".format(GeneInfo.objects.count()))
        GeneInfo.objects.all().delete()

    existing_gene_ids = {gene.gene_id for gene in GeneInfo.objects.all().only('gene_id')}
    existing_transcript_ids = {
        transcript.transcript_id for transcript in TranscriptInfo.objects.all().only('transcript_id')
    }

    new_genes, new_transcripts, counters = load_gencode_records(
        gencode_release, gencode_gtf_path, genome_version, existing_gene_ids, existing_transcript_ids)

    logger.info('Creating {} GeneInfo records'.format(len(new_genes)))
    counters["genes_created"] = len(new_genes)
    GeneInfo.objects.bulk_create([GeneInfo(**record) for record in new_genes.values()])

    counters["transcripts_created"] = len(new_transcripts)
    create_transcript_info(new_transcripts)

    logger.info("Done")
    logger.info("Stats: ")
    for k, v in counters.items():
        logger.info("  %s: %s" % (k, v))
