import logging
from django.core.management.base import BaseCommand

from reference_data.models import HumanPhenotypeOntology

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Downloads the latest hp.obo release and update the HumanPhenotypeOntology table"

    def handle(self, *args, **options):
        HumanPhenotypeOntology.update_records()