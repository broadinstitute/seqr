from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import ClinGen

class ClinGenReferenceDataHandler(ReferenceDataHandler):

    model_cls = ClinGen

class Command(GeneCommand):
    reference_data_handler = ClinGenReferenceDataHandler
