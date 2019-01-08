from django.core.management.base import BaseCommand
import re

from seqr.models import Individual, ProjectCategory
from seqr.views.apis.individual_api import export_individuals


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('projects', nargs='*')
        parser.add_argument("--project-category")

    def handle(self, *args, **options):
        project_names = options.get('projects')
        if options.get('project_category'):
            project_names += [p.name for p in ProjectCategory.objects.get(name=options['project_category']).projects.all()]

        if not len(project_names):
            raise Exception('Error: No projects specified')
        print('Exporting individuals from {} projects'.format(len(project_names)))

        individuals = Individual.objects.filter(family__project__name__in=project_names).all()
        print('Found {} individuals to export'.format(len(individuals)))
        response = export_individuals(
            'projects_individuals',
            individuals,
            'xls',
            include_project_name=True,
            include_project_created_date=True,
            include_created_date=True,
            include_analysis_status=True,
            include_coded_phenotype=True,
            include_hpo_terms_present=True,
            include_hpo_terms_absent=True,
            include_first_loaded_date=True,
        )
        print('Parsed individual data')
        filename = re.search('filename="(?P<file_name>.*)"', response.get('Content-Disposition')).group('file_name')
        with open(filename, 'w') as f:
            f.write(response.content)
        print('Wrote results to {}'.format(filename))