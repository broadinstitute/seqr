from django.core.management.base import BaseCommand

from reference_data.management.commands.update_all_reference_data import update_all_reference_data_sources
from reference_data.models import GeneInfo, HumanPhenotypeOntology

REFERENCE_DATA_MODELS = {
    'gencode': GeneInfo,
    'hpo': HumanPhenotypeOntology,
}

class Command(BaseCommand):
    help = 'Loads all missing reference data sources'

    def handle(self, *args, **options):
        update_all_reference_data_sources(self._should_skip)

    @staticmethod
    def _should_skip(source, data_handler):
        model_cls = data_handler.model_cls if data_handler else REFERENCE_DATA_MODELS[source]
        return model_cls.objects.exists()
