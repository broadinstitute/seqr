from django.core.management.base import BaseCommand, CommandError
from seqr.models import Dataset
from django.core.exceptions import ObjectDoesNotExist

class Command(BaseCommand):
    help = 'Delete dataset.'

    def add_arguments(self, parser):
        parser.add_argument('dataset_id', help="Dataset id")

    def handle(self, *args, **options):
        dataset_id = options.get('dataset_id')
        print("Deleting dataset: %s" % dataset_id)
        try:
            dataset = Dataset.objects.get(guid=dataset_id)
        except ObjectDoesNotExist:
            raise CommandError("Dataset %s not found." % dataset_id)

        dataset.delete()

        print("Deleted %s!" % dataset_id)


