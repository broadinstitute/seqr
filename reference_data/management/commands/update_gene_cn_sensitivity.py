import logging
from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import GeneCopyNumberSensitivity

logger = logging.getLogger(__name__)


class CNSensitivityReferenceDataHandler(ReferenceDataHandler):

    model_cls = GeneCopyNumberSensitivity

class Command(GeneCommand):
    reference_data_handler = CNSensitivityReferenceDataHandler
