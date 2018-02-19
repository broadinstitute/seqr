import logging
import os
from tqdm import tqdm
import urllib

from django.core.management.base import BaseCommand

from reference_data.models import Clinvar

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        url_prefix = "http://github.com/..." % locals()

        logger.info("Done")
