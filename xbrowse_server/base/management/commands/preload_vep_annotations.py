from optparse import make_option

from django.core.management.base import BaseCommand

import tasks


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--overwrite', action='store_true', dest='overwrite', default=False),
    )

    def handle(self, *args, **options):
        for vcf_path in args:
            tasks.preload_vep_vcf_annotations.delay(vcf_path)
