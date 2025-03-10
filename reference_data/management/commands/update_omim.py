import logging
import os

from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import Omim

logger = logging.getLogger(__name__)

class CachedOmimReferenceDataHandler(ReferenceDataHandler):

    model_cls = Omim

class OmimReferenceDataHandler(ReferenceDataHandler):

    model_cls = Omim

class Command(GeneCommand):
    reference_data_handler = OmimReferenceDataHandler

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration", default=os.environ.get("OMIM_KEY"))
        parser.add_argument('--skip-cache-parsed-records', action='store_true', help='write the parsed records to google storage for reuse')
        super(Command, self).add_arguments(parser)
