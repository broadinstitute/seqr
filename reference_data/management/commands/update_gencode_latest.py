import logging

from django.core.management.base import BaseCommand

from reference_data.management.commands.utils.gencode_utils import load_gencode_records, create_transcript_info, \
    LATEST_GENCODE_RELEASE
from reference_data.models import GeneInfo, TranscriptInfo, GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38

logger = logging.getLogger(__name__)

BATCH_SIZE = 10000


class Command(BaseCommand):
    help = 'Loads the GRCh37 and/or GRCh38 versions of the Gencode GTF from a particular Gencode release, updating previously loaded gencode data'

    def add_arguments(self, parser):
        parser.add_argument('--track-symbol-change', action='store_true')

    def handle(self, *args, **options):
        genes, transcripts, counters = load_gencode_records(LATEST_GENCODE_RELEASE)

        genes_to_update = GeneInfo.objects.filter(gene_id__in=genes.keys())
        fields = set()
        symbol_changes = {}
        for existing_gene in genes_to_update:
            new_gene = genes.pop(existing_gene.gene_id)
            if options['track_symbol_change'] and new_gene['gene_symbol'] != existing_gene.gene_symbol:
                symbol_changes[new_gene['gene_symbol']] = f'{existing_gene.gene_symbol} (release {existing_gene.gencode_release})'
            fields.update(new_gene.keys())
            for key, value in new_gene.items():
                setattr(existing_gene, key, value)

        logger.info('Updating {} previously loaded GeneInfo records'.format(len(genes_to_update)))
        counters['genes_updated'] = len(genes_to_update)
        GeneInfo.objects.bulk_update(genes_to_update, fields, batch_size=BATCH_SIZE)

        logger.info('Creating {} GeneInfo records'.format(len(genes)))
        counters['genes_created'] = len(genes)
        GeneInfo.objects.bulk_create([GeneInfo(**record) for record in genes.values()], batch_size=BATCH_SIZE)

        # Transcript records have no child models, so safe to delete and recreate
        existing_transcripts = TranscriptInfo.objects.filter(transcript_id__in=transcripts.keys())
        counters['transcripts_recreated'] = len(existing_transcripts)
        counters['transcripts_created'] = len(transcripts) - len(existing_transcripts)
        existing_transcripts.delete()
        create_transcript_info(transcripts)

        logger.info('Done')
        if options['track_symbol_change']:
            logger.info('Gene Symbol Changes:')
            changes = sorted([f'{v}: k' for k, v in symbol_changes.items()])
            for change in changes:
                logger.info(change)
        logger.info('Stats: ')
        for k, v in counters.items():
            logger.info('  %s: %s' % (k, v))
