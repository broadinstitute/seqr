import os

from django.core.management.base import CommandError

from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import Omim

class CachedOmimReferenceDataHandler(ReferenceDataHandler):

    model_cls = Omim

class OmimReferenceDataHandler(ReferenceDataHandler):

    model_cls = Omim

    def __init__(self, omim_key=None, **kwargs):
        if not omim_key:
            raise CommandError("omim_key is required")

        self.omim_key = omim_key
        super().__init__(**kwargs)

    def update_records(self, **kwargs):
        super().update_records(omim_key=self.omim_key, **kwargs)

class Command(GeneCommand):
    reference_data_handler = OmimReferenceDataHandler

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration", default=os.environ.get("OMIM_KEY"))
        super(Command, self).add_arguments(parser)
