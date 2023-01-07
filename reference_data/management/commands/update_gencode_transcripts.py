import logging

from django.core.management.base import BaseCommand

from reference_data.management.commands.utils.gencode_utils import load_gencode_records, create_transcript_info, \
    LATEST_GENCODE_RELEASE
from reference_data.models import TranscriptInfo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reloads just the Gencode transcripts from the latest Gencode release"

    def handle(self, *args, **options):
        transcripts = TranscriptInfo.objects.filter(gene__gencode_release=LATEST_GENCODE_RELEASE)
        logger.info("Dropping the {} existing TranscriptInfo entries".format(transcripts.count()))
        transcripts.delete()

        _, new_transcripts, _ = load_gencode_records(LATEST_GENCODE_RELEASE)
        create_transcript_info(new_transcripts)
