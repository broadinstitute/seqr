import logging

from django.core.management.base import BaseCommand

from reference_data.management.commands.utils.gencode_utils import load_gencode_records, create_transcript_info, \
    LATEST_GENCODE_RELEASE
from reference_data.management.commands.update_refseq import RefseqReferenceDataHandler
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

        genes, transcripts, counters = load_gencode_records(LATEST_GENCODE_RELEASE)

        genes_to_update = GeneInfo.objects.filter(gene_id__in=genes.keys())
        fields = set()
        symbol_changes = []
        for existing in genes_to_update:
            new_gene = genes.pop(existing.gene_id)
            if track_symbol_change and new_gene['gene_symbol'] != existing.gene_symbol:
                symbol_changes.append((existing.gene_id, existing.gene_symbol, new_gene['gene_symbol']))
            fields.update(new_gene.keys())
            for key, value in new_gene.items():
                setattr(existing, key, value)

        if symbol_changes:
            with open(f'{options.get("output_directory", ".")}/gene_symbol_changes.csv', 'w') as f:
                f.writelines(sorted([f'{",".join(change)}\n' for change in symbol_changes]))

        logger.info(f'Updating {len(genes_to_update)} previously loaded GeneInfo records')
        counters['genes_updated'] = len(genes_to_update)
        GeneInfo.objects.bulk_update(genes_to_update, fields, batch_size=BATCH_SIZE)

        logger.info('Creating {} GeneInfo records'.format(len(genes)))
        counters['genes_created'] = len(genes)
        GeneInfo.objects.bulk_create([GeneInfo(**record) for record in genes.values()], batch_size=BATCH_SIZE)

        # Transcript records child models are also from gencode, so better to reset all data and then repopulate
        existing_transcripts = TranscriptInfo.objects.filter(transcript_id__in=transcripts.keys())
        counters['transcripts_replaced'] = len(existing_transcripts)
        counters['transcripts_created'] = len(transcripts) - len(existing_transcripts)
        logger.info(f'Dropping {len(existing_transcripts)} existing TranscriptInfo entries')
        existing_transcripts.delete()
        create_transcript_info(transcripts)

        RefseqReferenceDataHandler().update_records()

        logger.info('Done')
        logger.info('Stats: ')
        for k, v in counters.items():
            logger.info(f'  {k}: {v}')
