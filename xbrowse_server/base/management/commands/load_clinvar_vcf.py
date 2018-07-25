from django.core.management import BaseCommand
from xbrowse_server.mall import get_reference


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?', help="Path of clinvar vcf file")

    def handle(self, *args, **options):
        get_reference()._load_clinvar(options['path'])

