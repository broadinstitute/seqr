from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import dbNSFPGene

class DbNSFPReferenceDataHandler(ReferenceDataHandler):

    model_cls = dbNSFPGene

class Command(GeneCommand):
    reference_data_handler = DbNSFPReferenceDataHandler
