from optparse import make_option
import gzip
import sys
import os
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project
from xbrowse_server import sample_management
from xbrowse.parsers import vcf_stuff
from xbrowse_server.phenotips.utilities import add_individuals_to_phenotips_from_ped
from xbrowse_server.phenotips.utilities import add_individuals_to_phenotips_from_vcf
from xbrowse_server.phenotips.utilities import phenotype_entry_metric_for_individual

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--summerize',
                    '-s',
                    dest='summarize',
                    help='Summarize patient counts.',
                    action='store_true'
                    ),
        make_option('--list_of_projects',
                    '-l',
                    dest='list_of_projects',
                    help='A list of projects to gather metrics',
                    ),
    )

    def handle(self, *args, **options):
      '''
        Handles gathering of phenotype entry status from Phenotips for a given project
      '''
      
      if not options['list_of_projects'] and len(args)==0:
        print '\n\nGathers phenotype entry status from Phenotips for a given project.\n'
        print 'Please enter a project ID (first positional argument).'
        print '\n'
        sys.exit()
      proj_dets={}
      try:
        if not options['list_of_projects']:
          project_id = args[0]
          proj_dets[project_id]=self.process_project(project_id)
        else:
          if os.path.exists(options['list_of_projects']):
            with open(options['list_of_projects'],'r') as proj_list_in:
              for proj in proj_list_in:
                proj_dets[proj.rstrip()]=self.process_project(proj.rstrip())
            proj_list_in.close()
        self.print_details_to_stdout(proj_dets,options['summarize'])
      except Exception as e:
        print '\nsorry, we encountered an error finding project:',e,'\n'
        sys.exit()
        
        
    def process_project(self,project_id):
      '''
        Processes the given project
        Inputs:
        project: a project ID
      '''
      try:
          project = Project.objects.get(project_id=project_id)
          individuals=[]
          for individual in project.get_individuals():
            individuals.append(individual.indiv_id)
          return self.get_phenotype_entry_details_for_individuals(individuals,project_id)
      except Exception as e:
        print '\nsorry, we encountered an error finding project:',e,'\n'
        raise
      


    def get_phenotype_entry_details_for_individuals(self,individuals,project_id):
      '''
        Process this list of individuals
        
        Inputs:
        individuals: a list of individuals
      '''
      all_patients=[]
      try:
        for individual in individuals:
          phenotype_count_for_indiv=phenotype_entry_metric_for_individual(individual,project_id)
          all_patients.append({'eid':individual,'num_phenotypes_entered':phenotype_count_for_indiv})
        return all_patients
      except Exception as e:
        raise
   
       
       

    def print_details_to_stdout(self,proj_dets,summarize):
      '''
        Print details to STDOUT
        
        Inputs:
        proj_dets: a project details structure
        summarize: True/False whether to summarize view
      '''
      category_names=self.get_phenotype_count_categorie_names()
      if summarize:
          print '{:20s} {:20s} {:20s} {:20s} {:20s} {:20s}'.format('Project',*category_names)
      try:
        for proj_id,dets in proj_dets.iteritems():
          phenotype_counts={}
          for patient_det in dets:
            if not summarize:
              print patient_det['eid'],patient_det['num_phenotypes_entered']
            if summarize:
              if phenotype_counts.has_key(patient_det['num_phenotypes_entered']):
                phenotype_counts[patient_det['num_phenotypes_entered']].append(patient_det['eid'])
              else:
                phenotype_counts[patient_det['num_phenotypes_entered']]=[patient_det['eid']]
          if summarize:
            data=self.categorize_phenotype_counts(phenotype_counts)
            print '{:20s}'.format(proj_id),
            for category_name in category_names:
              print '{:20s}'.format(str(len(data[category_name]))),
            print
      except Exception as e:
        raise
        
        
    def categorize_phenotype_counts(self,phenotype_counts):
      '''
        Bin counts in categories for easy reporting in columns
        
        Categories are:
        0
        0-10
        10-20
        >30
        
        Notes:
        If you add any new categories, remember to update method
        get_phenotype_count_categorie_names.
        
        Inputs:
        A dict of number of patients to number of phenotypes 
        entered for each patient 
        
        Outputs:
        -A dict with keys of above categories and values being count
        of each.
        -A tuple with category names
      '''
      category_names=self.get_phenotype_count_categorie_names()
      data={}
      for c in category_names:
        data[c]=[]
      for phenotype_count,patients in phenotype_counts.iteritems():
        if phenotype_count ==0:
          data['0'].extend(patients)
        if phenotype_count>0 and phenotype_count<11:
          data['1-10'].extend(patients) 
        if phenotype_count>=11 and phenotype_count<=20:
          data['11-20'].extend(patients)
        if phenotype_count>=21 and phenotype_count<=30:
          data['21-30'].extend(patients)
        if phenotype_count>=31:
          data['>31'].extend(patients)
      return data
    
    
    def get_phenotype_count_categorie_names(self):
      '''
        Return a tuple of category names used
        categorize_phenotype_counts.
        Notes:
        Any updates to this function must coincide with method
        
      '''
      return ('0','1-10','11-20','21-30','>31')