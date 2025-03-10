from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import MGI

class MGIReferenceDataHandler(ReferenceDataHandler):

    model_cls = MGI

class Command(GeneCommand):
    reference_data_handler = MGIReferenceDataHandler
