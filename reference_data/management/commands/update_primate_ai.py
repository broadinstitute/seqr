from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import PrimateAI


class PrimateAIReferenceDataHandler(ReferenceDataHandler):

    model_cls = PrimateAI

class Command(GeneCommand):
    reference_data_handler = PrimateAIReferenceDataHandler
