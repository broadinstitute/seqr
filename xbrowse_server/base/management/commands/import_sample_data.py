import json

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project, Individual, Family, ProjectPhenotype, IndividualPhenotype
from xbrowse_server import sample_management


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):

        project = Project.objects.get(project_id=args[0])
        d = json.load(open(args[1]))

        # create families
        for family_d in d['families']:
            family = Family.objects.get_or_create(project=project, family_id=family_d['family_id'])[0]
            family.family_name = family_d['family_name']
            family.analysis_status = family_d['analysis_status']
            family.save()

        # individuals
        for indiv_d in d['individuals']:
            individual = Individual.objects.get_or_create(project=project, indiv_id=indiv_d['indiv_id'])[0]
            individual.nickname = indiv_d['nickname']
            individual.gender = indiv_d['gender']
            individual.affected = indiv_d['affected']
            individual.maternal_id = indiv_d['maternal_id']
            individual.paternal_id = indiv_d['paternal_id']
            individual.other_notes = indiv_d['other_notes']
            individual.save()
            sample_management.set_family_id_for_individual(individual, indiv_d['family_id'])

        # phenotypes
        for pheno_d in d['project_phenotypes']:
            pheno = ProjectPhenotype.objects.get_or_create(slug=pheno_d['slug'], project=project)[0]
            pheno.name = pheno_d['name']
            pheno.category = pheno_d['category']
            pheno.datatype = pheno_d['datatype']
            pheno.save()

        for ipheno_d in d['indiv_phenotypes']:
            indiv = Individual.objects.get(project=project, indiv_id=ipheno_d['indiv_id'])
            phenotype = ProjectPhenotype.objects.get(project=project, slug=ipheno_d['slug'])
            ipheno = IndividualPhenotype.objects.get_or_create(phenotype=phenotype, individual=indiv)[0]
            ipheno.boolean_val = None
            ipheno.float_val = None
            if phenotype.datatype == 'bool':
                ipheno.boolean_val = ipheno_d['val']
            ipheno.save()