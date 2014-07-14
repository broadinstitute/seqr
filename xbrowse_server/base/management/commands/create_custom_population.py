from optparse import make_option
import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ReferencePopulation


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--name'),
        make_option('--file_type'),
        make_option('--file_path'),
    )

    def handle(self, *args, **options):

        slug = args[0]
        if ReferencePopulation.objects.filter(slug=args[0]).exists():
            raise Exception("Already exists")
        else:
            population = ReferencePopulation.objects.create(slug=slug)

        if options.get('name'):
            population.name = options.get('name')
        else:
            population.name = slug
        if options.get('file_type'):
            population.file_type = options.get('file_type')
        if options.get('file_path'):
            population.file_path = os.path.abspath(options.get('file_path'))

        population.save()
