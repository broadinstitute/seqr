from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import RefseqTranscript

class RefseqReferenceDataHandler(ReferenceDataHandler):

    model_cls = RefseqTranscript

class Command(GeneCommand):
    reference_data_handler = RefseqReferenceDataHandler
