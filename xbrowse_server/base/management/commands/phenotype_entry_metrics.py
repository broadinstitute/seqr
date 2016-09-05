import sys
import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
from xbrowse_server.phenotips.reporting_utilities import phenotype_entry_metric_for_individual


__VERSION__ = 0.2

class Command(BaseCommand):
    
    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('--project_id')
        
    def handle(self, *args, **options):
        """
        Handles gathering of phenotype entry status from Phenotips for a given project
        """

        if not options.get('project_id'):
            print '\n\nGathers phenotype entry status from Phenotips for a given project.\n'
            print 'Please enter a project ID with "--project_id".'
            print '\n'
            sys.exit()
        else:
            project_id=options.get('project_id')
            self.process_project(project_id)

    def process_project(self, project_id):
        """
        Processes the given project

        Args:
            project_id: a project ID
        """
        try:
            project = Project.objects.get(project_id=project_id)
            individuals = []
            for individual in project.get_individuals():
                individuals.append(individual.phenotips_id)
            phenotypes=self.get_phenotypes_for_individuals(project_id, individuals)
            for phenotype in phenotypes:
                print phenotype['id'],'\t',
                hpos=''
                
                if phenotype['phenotypes']['raw'].has_key('features'):
                    for i,p in enumerate(phenotype['phenotypes']['raw']['features']):
                        hpos += p['id']
                        if i<len(phenotype['phenotypes']['raw']['features'])-1:
                            hpos += ','
                if phenotype['phenotypes']['raw'].has_key('nonstandard_features') and len(phenotype['phenotypes']['raw']['nonstandard_features'])>0:
                    hpos += ','
                    for i,p in enumerate(phenotype['phenotypes']['raw']['nonstandard_features']):
                        hpos += p['id']
                        if i<len(phenotype['phenotypes']['raw']['nonstandard_features'])-1:
                            hpos += ','
                print hpos
        except Exception as e:
            print '\nsorry, we encountered an error:', e, '\n'
            raise


    def get_phenotypes_for_individuals(self, project_id, individuals):
        """
          Get phenotypes for this list of individuals
          
          Inputs:
          individuals: a list of individuals
        """
        all_patients = []
        for individual in individuals:
            phenotypes  = phenotype_entry_metric_for_individual(project_id, individual)
            all_patients.append({'id': individual, 'phenotypes': phenotypes})
        return all_patients

