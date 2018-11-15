import logging

from django.core.management.base import BaseCommand
from django.db.models import F

from seqr.models import Family, Individual

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer family groups to the new seqr schema'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        updated = Family.objects.filter(display_name=F('family_id')).update(display_name='')
        logger.info("Updated {} families".format(updated))

        updated = Individual.objects.filter(display_name=F('individual_id')).update(display_name='')
        logger.info("Updated {} individuals".format(updated))

