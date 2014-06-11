from django.core.management.base import BaseCommand

from django.conf import settings
from xbrowse_server.base.models import Individual, Family, Project

class Command(BaseCommand):
    """
    Management command to initialize an xbrowse server from an xbrowse datastore
    """
    def handle(self, *args, **options):

        datastore = settings.DATASTORE

        # add all individuals
        for indiv in Individual.objects.all():
            if not datastore.individual_exists(indiv.project.project_id, indiv.indiv_id):
                datastore.add_individual(indiv.project.project_id, indiv.indiv_id)

        # add all families/cohorts
        for project in Project.objects.all():

            for vcf_file, families in project.families_by_vcf().items():
                family_list = []
                for family in families:
                    family_list.append({
                        'project_id': family.project.project_id,
                        'family_id': family.family_id,
                        'individuals': family.indiv_id_list(),
                    })
                datastore.add_family_set(settings.REFERENCE, family_list)
