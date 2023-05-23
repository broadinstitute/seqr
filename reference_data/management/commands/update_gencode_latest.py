import logging

from django.core.management.base import BaseCommand

from reference_data.management.commands.utils.gencode_utils import load_gencode_records, create_transcript_info, \
    map_transcript_gene_ids, LATEST_GENCODE_RELEASE
from reference_data.models import GeneInfo, TranscriptInfo, GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000


class Command(BaseCommand):
    help = 'Loads genes and transcripts from the latest supported Gencode release, updating previously loaded gencode data'

    def add_arguments(self, parser):
        parser.add_argument('--track-symbol-change', action='store_true')
        parser.add_argument('--output-directory')

    def handle(self, *args, **options):
        genes, transcripts, counters = load_gencode_records(LATEST_GENCODE_RELEASE)

        self.update_existing_models(
            genes, GeneInfo, counters, 'gene_id', output_directory=options.get('output_directory'),
            track_change_field='gene_symbol' if options['track_symbol_change'] else None,
        )

        logger.info('Creating {} GeneInfo records'.format(len(genes)))
        counters['geneinfo_created'] = len(genes)
        GeneInfo.objects.bulk_create([GeneInfo(**record) for record in genes.values()], batch_size=BATCH_SIZE)

        map_transcript_gene_ids(transcripts)
        self.update_existing_models(transcripts, TranscriptInfo, counters, 'transcript_id')

        counters['transcriptinfo_created'] = len(transcripts)
        create_transcript_info(transcripts, skip_gene_id_mapping=True)

        logger.info('Done')
        logger.info('Stats: ')
        for k, v in counters.items():
            logger.info('  %s: %s' % (k, v))

    @staticmethod
    def update_existing_models(new_data, model_cls, counters, id_field, track_change_field=None, output_directory='.'):
        models_to_update = model_cls.objects.filter(**{f'{id_field}__in': new_data.keys()})
        fields = set()
        changes = []
        for existing in models_to_update:
            model_id = getattr(existing, id_field)
            new = new_data.pop(model_id)
            if track_change_field and new[track_change_field] != getattr(existing, track_change_field):
                changes.append((model_id, getattr(existing, track_change_field), new[track_change_field]))
            fields.update(new.keys())
            for key, value in new.items():
                setattr(existing, key, value)

        logger.info(f'Updating {len(models_to_update)} previously loaded {model_cls.__name__} records')
        counters[f'{model_cls.__name__.lower()}_updated'] = len(models_to_update)
        model_cls.objects.bulk_update(models_to_update, fields, batch_size=BATCH_SIZE)

        if changes:
            with open(f'{output_directory}/{track_change_field}_changes.csv', 'w') as f:
                f.writelines(sorted([f'{",".join(change)}\n' for change in changes]))
