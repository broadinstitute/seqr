from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneShet


class ShetReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneShet

class Command(GeneCommand):
    reference_data_handler = ShetReferenceDataHandler
