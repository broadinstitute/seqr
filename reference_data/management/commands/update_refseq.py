import logging
from django.core.management.base import CommandError

from reference_data.management.commands.utils.gencode_utils import GENCODE_URL_TEMPLATE, LATEST_GENCODE_RELEASE
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import TranscriptInfo, RefseqTranscript

logger = logging.getLogger(__name__)


class RefseqReferenceDataHandler(ReferenceDataHandler):

    model_cls = RefseqTranscript
    url = GENCODE_URL_TEMPLATE.format(path='', file='.metadata.RefSeq.gz', gencode_release=LATEST_GENCODE_RELEASE)
    gene_key = 'transcript'

    def __init__(self, **kwargs):
        if TranscriptInfo.objects.count() == 0:
            raise CommandError("TranscriptInfo table is empty. Run './manage.py update_gencode' before running this command.")

        self.transcript_id_map = {
            t.transcript_id: t for t in TranscriptInfo.objects.all().only('transcript_id')
        }

    @staticmethod
    def get_file_header(f):
        return ['transcript_id', 'refseq_id', 'additional_info']

    @staticmethod
    def parse_record(record):
        yield {
            'transcript_id': record['transcript_id'].split('.')[0],
            'refseq_id': record['refseq_id'],
        }

    def get_gene_for_record(self, record):
        transcript_id = record.pop('transcript_id')
        # only create a record for the first occurrence of a given transcript
        transcript = self.transcript_id_map.pop(transcript_id, None)

        if not transcript:
            raise ValueError(f'Transcript "{transcript_id}" not found in the TranscriptInfo table')
        return transcript


class Command(GeneCommand):
    reference_data_handler = RefseqReferenceDataHandler
