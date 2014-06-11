from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from xbrowse_server.base.models import VCFFile
import tasks

class Command(BaseCommand):
    def handle(self, *args, **options):
        for vcf in VCFFile.objects.all():
            tasks.re_run_vep.delay(vcf.path())
