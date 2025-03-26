from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GenCC

class GenCCReferenceDataHandler(ReferenceDataHandler):

    model_cls = GenCC

class Command(GeneCommand):
    reference_data_handler = GenCCReferenceDataHandler
