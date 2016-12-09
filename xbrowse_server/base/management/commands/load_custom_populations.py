from optparse import make_option
from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand
from django.conf import settings
from xbrowse_server.base.models import ReferencePopulation
import sys

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

        parser.add_argument('--AF-key', help="The VCF info field key corresponding the to AF")
        parser.add_argument('--AC-key', help="The VCF info field key corresponding the to AC")
        parser.add_argument('--AN-key', help="The VCF info field key corresponding the to AN")

    def handle(self, *args, **options):
        from xbrowse_server import mall
        if len(args) == 0:
            print("Global: " + str([slug for slug in settings.ANNOTATOR_REFERENCE_POPULATION_SLUGS]))
            print("Private: " + str([p.slug for p in ReferencePopulation.objects.all()]))
        else:
            pop_store = mall.get_custom_population_store()
            pop_store._ensure_indices()

            population_id = args[0]
            populations = [p for p in settings.ANNOTATOR_REFERENCE_POPULATIONS if p["slug"] == population_id] + \
                       [p.to_dict() for p in ReferencePopulation.objects.all() if p.slug == population_id]

            assert len(populations) == 1
            population_dict = populations[0]
            if options["AF_key"]:
                population_dict["vcf_info_key"] = options["AF_key"]
            elif options["AC_key"] and options["AN_key"]:
                population_dict["ac_info_key"] = options["AC_key"]
                population_dict["an_info_key"] = options["AN_key"]
            elif population_dict['file_type'].startswith('sites_vcf'):
                sys.exit("Must specify either --AF-key or both --AC-key and --AN-key")

            print("Loading pouplation: " + population_id + " " + str(population_dict))
            pop_store.load_population(population_dict)


        #[{'slug': s['slug'], 'name': s['name']} for s in settings.ANNOTATOR_REFERENCE_POPULATIONS] +
        #[{'slug': s.slug, 'name': s.name} for s in self.private_reference_populations.all()]

