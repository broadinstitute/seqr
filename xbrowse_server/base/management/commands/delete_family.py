from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Family, Individual, Cohort, FamilyGroup

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-p', '---project', required=True)
        parser.add_argument('args', nargs="+", help='family ids')

    def handle(self, *args, **options):
        project_id = options['project']
        family_ids = args
        
        for family_id in family_ids:
            f = Family.objects.get(project__project_id=project_id, family_id=family_id)
            i = raw_input("Will delete family: " + str(f) +". Continue? [y/n] ") 
            if i.lower() != 'y':
                print("Skipping")
                continue
            print("Deleting: " + str(f))
            f.delete()
