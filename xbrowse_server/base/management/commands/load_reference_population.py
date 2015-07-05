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

        # Go through each project in decending order
        population_slugs_to_load = [population_spec['slug'] for population_spec in annotator_settings.reference_populations_to_load]
        for project in Project.objects.all().order_by('-last_accessed_date'):
            project_id = project.project_id
            datastore = get_datastore(project_id)
            for family_info in datastore._get_family_info(project_id):
                family_id = family_info['family_id']
                family_collection = datastore._get_family_collection(project_id, family_id)
                print("{'project': %s, 'family_id': %s}" % (project_id, family_id))
                for variant_dict in family_collection.find():
                    freqs = population_frequency_store.get_frequencies(variant_dict['xpos'], variant_dict['ref'], variant_dict['alt'])
                    full_freqs = {popupalation_slug: freqs.get(popupalation_slug, 0) for population_slug in population_slugs_to_load}

                    print("    variant_dict: %s, freqs: %s" % (variant_dict, full_freqs))