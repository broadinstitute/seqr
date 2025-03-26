from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneConstraint


class GeneConstraintReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneConstraint

class Command(GeneCommand):
    reference_data_handler = GeneConstraintReferenceDataHandler
