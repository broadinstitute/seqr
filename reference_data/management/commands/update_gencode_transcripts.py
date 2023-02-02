import logging

from django.core.management.base import BaseCommand

from reference_data.management.commands.utils.gencode_utils import load_gencode_records, create_transcript_info, \
    LATEST_GENCODE_RELEASE
from reference_data.models import TranscriptInfo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reloads just the Gencode transcripts from the latest Gencode release"

    def add_arguments(self, parser):
        parser.add_argument('--gencode-release', help="gencode release number (eg. 28)", type=int, required=True,
                            choices=range(19, 40))

    def handle(self, *args, **options):
        gencode_release = options.get('gencode_release', LATEST_GENCODE_RELEASE)
        print(f'Using GENCODE release: {gencode_release}')
        transcripts = TranscriptInfo.objects.filter(gene__gencode_release=gencode_release)
        logger.info("Dropping the {} existing TranscriptInfo entries".format(transcripts.count()))
        transcripts.delete()

        _, new_transcripts, _ = load_gencode_records(gencode_release)
        create_transcript_info(new_transcripts)
