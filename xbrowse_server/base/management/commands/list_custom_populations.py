from optparse import make_option
import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ReferencePopulation


class Command(BaseCommand):


    def add_arguments(self, parser):
        #parser.add_argument('args', nargs='*')
        pass

    def handle(self, *args, **options):

        for p in sorted(ReferencePopulation.objects.all(), key=lambda p: p.slug):
            print("%s: %s   - %s  %s" % (p.slug, p.name, p.file_type, p.file_path))

