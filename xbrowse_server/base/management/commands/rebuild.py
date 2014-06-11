from optparse import make_option
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--all', action="store_true", default="False"),
        make_option('--reference', action="store_true", default="False"),
        make_option('--popfreq', action="store_true", default="False"),
    )

    def handle(self, *args, **options):

        # not sure why `is True` is necessary here...
        if options.get('reference') is True or options.get('all') is True:
            settings.REFERENCE.load()

        if options.get('popfreq') is True or options.get('all') is True:
            settings.POPULATION_FREQUENCY_STORE.load()