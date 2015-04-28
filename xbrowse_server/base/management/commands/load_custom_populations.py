from optparse import make_option
from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand
from django.conf import settings
from xbrowse_server.base.models import ReferencePopulation

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--some-option'),
    )


    def handle(self, *args, **options):
        from xbrowse_server import mall
        if len(args) == 0:
            print("Global: " + str([slug for slug in settings.ANNOTATOR_REFERENCE_POPULATION_SLUGS]))
            print("Private: " + str([p.slug for p in ReferencePopulation.objects.all()]))
        else:
            pop_store = mall.get_custom_population_store()
            pop_store._ensure_indices()
            print("Loading population: " + args[0])

            requested_slug = args[0]
            projects = [p for p in settings.ANNOTATOR_REFERENCE_POPULATIONS if p["slug"] == requested_slug] + \
                [p.to_dict() for p in ReferencePopulation.objects.all() if p.slug == requested_slug]

            assert len(projects) == 1
            pop_store.load_population(projects[0])


        #[{'slug': s['slug'], 'name': s['name']} for s in settings.ANNOTATOR_REFERENCE_POPULATIONS] +
        #[{'slug': s.slug, 'name': s.name} for s in self.private_reference_populations.all()]

