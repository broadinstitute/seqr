import logging

from django.core.management.base import BaseCommand

from reference_data.management.commands.update_refseq import RefseqReferenceDataHandler
from reference_data.utils.gene_utils import get_genes_by_id_and_symbol
from reference_data.models import GeneInfo, TranscriptInfo

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000


class Command(BaseCommand):
    help = 'Loads genes and transcripts from the latest supported Gencode release, updating previously loaded gencode data'

    def add_arguments(self, parser):
        parser.add_argument('--track-symbol-change', action='store_true')
        parser.add_argument('--output-directory')

    def handle(self, *args, **options):
        track_symbol_change = options['track_symbol_change']

        symbol_changes = [] if track_symbol_change else None
        transcripts = GeneInfo.update_records(symbol_changes=symbol_changes)

        if symbol_changes:
            with open(f'{options.get("output_directory", ".")}/gene_symbol_changes.csv', 'w') as f:
                f.writelines(sorted([f'{",".join(change)}\n' for change in symbol_changes]))

        # Transcript records child models are also from gencode, so better to reset all data and then repopulate
        existing_transcripts = TranscriptInfo.objects.filter(transcript_id__in=transcripts.keys())
        deleted, _ = existing_transcripts.delete()
        logger.info(f'Dropped {deleted} existing TranscriptInfo records')

        gene_id_map, _ = get_genes_by_id_and_symbol()
        TranscriptInfo.bulk_create_for_genes(transcripts, gene_id_map)

        RefseqReferenceDataHandler().update_records()
