
from django.core.management.base import BaseCommand, CommandError

from seqr.models import Project, Family, Individual
from seqr.views.apis.phenotips_api import delete_patient
from django.core.exceptions import ObjectDoesNotExist

class Command(BaseCommand):
    help = 'Delete all phenotips records for the given project.'

    def add_arguments(self, parser):
        parser.add_argument('project-id', help="All individuals in this project will be deleted from PhenoTips.")

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        print("Deleting phenotips records in project: %s" % project_id)
        try:
            proj = Project.objects.get(deprecated_project_id=project_id)
        except ObjectDoesNotExist:
            raise CommandError("Project %s not found." % project_id)

        for family in Family.objects.filter(project=proj):
            for individual in Individual.objects.filter(family=family):
                print("Deleting records for %s - %s" % (family.family_id, individual.individual_id))
                delete_patient(proj, individual)

        print("Deleted all phenotips records for %s!" % project_id)
