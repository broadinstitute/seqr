from django.conf import settings
from django.core.management import BaseCommand
from xbrowse_server import mall
from xbrowse_server.mall import get_reference, get_datastore
from xbrowse_server.xbrowse_annotation_controls import CustomAnnotator
from xbrowse_server.base.models import Project
import annotator_settings

class Command(BaseCommand):
    def handle(self, *args, **options):
        population_frequency_store = mall.get_annotator().get_population_frequency_store()
        for population_spec in annotator_settings.reference_populations_to_load:
            print("Loading " + str(population_spec))
            #population_frequency_store.load_population(population_spec)

        projects = Project.objects.all()
        for project in projects:
            datastore = get_datastore(project.project_id)
            print(datastore._get_family_info(project.project_id))
