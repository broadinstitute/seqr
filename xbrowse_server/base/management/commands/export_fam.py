from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+')

    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])
        for individual in project.get_individuals():
            famid = individual.family.family_id if individual.family else ""
            print "\t".join([
                    famid,
                    individual.indiv_id,
                    individual.paternal_id if individual.paternal_id else '.',
                    individual.maternal_id if individual.paternal_id else '.',
                    '2' if individual.gender == 'F' else ('1' if individual.gender == 'M' else '.'),
                    '2' if individual.affected == 'A' else ('1' if individual.affected == 'N' else '.'),
            ])
