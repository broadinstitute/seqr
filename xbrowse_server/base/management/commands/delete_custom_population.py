from optparse import make_option
import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ReferencePopulation


class Command(BaseCommand):

    def handle(self, *args, **options):
        if len(args) == 0:
            print("All custom reference populations:") 
            for rp in ReferencePopulation.objects.all():
                print(rp.slug)
        else:
            for arg in args:
                if not ReferencePopulation.objects.filter(slug=arg).exists():
                    raise Exception("Population id not found: " + arg)
            for arg in args:
                ReferencePopulation.objects.filter(slug=arg).delete()

