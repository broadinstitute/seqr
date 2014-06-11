from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Cohort


class Command(BaseCommand):
    def handle(self, *args, **options):
        project_id = args[0]
        cohort_id = args[1]
        cohort = Cohort.objects.get(project__project_id=project_id, cohort_id=cohort_id) 
        cohort.delete()
        print "Cohort {} / {} deleted".format(project_id, cohort_id)
