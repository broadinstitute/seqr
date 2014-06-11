from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from xbrowse_server.base.models import Project

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--no-phantoms', action="store_true", default="False"),
        )

    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])
        if options.get('no_phantoms'): 
            individuals = project.get_individuals()
        else: 
            individuals = project.get_individuals_with_variant_data()
        for individual in individuals:
            famid = individual.family.family_id if individual.family else ""
            print "\t".join([
                    famid,
                    individual.indiv_id,
                    individual.paternal_id,
                    individual.maternal_id,
                    '2' if individual.gender == 'F' else ('1' if individual.gender == 'M' else '.'),
                    '2' if individual.affected == 'A' else ('1' if individual.affected == 'N' else '.'),
            ])
