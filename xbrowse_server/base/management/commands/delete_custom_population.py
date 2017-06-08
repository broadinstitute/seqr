from optparse import make_option
import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ReferencePopulation


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        if len(args) == 0:
            print("This deletes a reference population from xBrowse as a whole (not from a specific project). To delete, specify a custom reference population id from the ones below: ")
            for rp in ReferencePopulation.objects.all():
                print(rp.slug)
        else:
            for arg in args:
                if not ReferencePopulation.objects.filter(slug=arg).exists():
                    raise Exception("Population id not found: " + arg)
            for arg in args:
                ReferencePopulation.objects.filter(slug=arg).delete()

