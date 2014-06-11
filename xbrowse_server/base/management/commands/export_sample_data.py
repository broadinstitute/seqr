from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, IndividualPhenotype
import json


class Command(BaseCommand):

    def handle(self, *args, **options):

        # collect all the data first
        project = Project.objects.get(project_id=args[0])
        individuals = project.get_individuals()
        families = project.get_families()
        project_phenotypes = project.get_phenotypes()
        indiv_phenotypes = IndividualPhenotype.objects.filter(phenotype__project=project)

        # populate data dict
        d = dict()

        # detailed individual data
        d['individuals'] = [indiv.to_dict() for indiv in individuals]

        d['families'] = [family.toJSON() for family in families]

        # phenotype schema for this project
        d['project_phenotypes'] = [phenotype.toJSON() for phenotype in project_phenotypes]

        d['indiv_phenotypes'] = [{
            'indiv_id': ipheno.individual.indiv_id,
            'slug': ipheno.phenotype.slug,
            'val': ipheno.val(),
        } for ipheno in indiv_phenotypes]

        print json.dumps(d)