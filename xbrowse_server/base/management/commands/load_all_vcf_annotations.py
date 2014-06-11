from django.core.management.base import BaseCommand
from xbrowse_server.base.models import VCFFile
import tasks

class Command(BaseCommand):
    def handle(self, *args, **options):
        for vcf in VCFFile.objects.all():
            tasks.preload_vep_vcf_annotations.delay(vcf.path())
