from __future__ import print_function
from optparse import make_option
import sys
import os
from django.core.management.base import BaseCommand
import json
import time
import datetime
from xbrowse_server.base.models import Individual
import logging
import hashlib
from cProfile import label

logger = logging.getLogger()
    
class Command(BaseCommand):
    """
    Generate a report of PhenoTips data available in seqr
    """
    __VERSION__ = 'v0.0.1'
    
    
    def handle(self,*args,**options):
        """
        Starting point for script
        
        Args:
            none needed
            
        Returns:
            Outputs a report
        """
        all_indivs = Individual.objects.all()
        unique_individuals={}
        for indiv in all_indivs:
            if unique_individuals.has_key(indiv.indiv_id):
                hpos = self.get_hpo_terms(indiv.phenotips_data)
                merged_hpos = self._merge_hpo_lists(unique_individuals[indiv.indiv_id]['phenotype_data'],hpos)
                unique_individuals[indiv.indiv_id]["phenotype_data"]=merged_hpos
            else:
                unique_individuals[indiv.indiv_id] = {"phenotype_data":self.get_hpo_terms(indiv.phenotips_data),
                                                      "affected_status":indiv.affected,
                                                      "project":indiv.project.project_id}
        print ("number of unique individuals (as same individual might be in different related projects): %s" % len(unique_individuals))                                              
        self.analyze(unique_individuals)


    def _merge_hpo_lists(self,hpos1,hpos2):
        """
        Given two dicts of HPOs, merge them into a unique set
        
        Args:
            hpos1 (dict): key is HPO term, value is label
            hpos2 (dict): key is HPO term, value is label
        
        Return:
            (dict): a merged dict of HPO to their label mappings
        """
        if len(hpos1)>len(hpos2):
            for id, label in hpos2.iteritems():
                if id not in hpos1:
                    hpos1[id]=label
            return hpos1
        else:
            for id, label in hpos1.iteritems():
                if id not in hpos2:
                    hpos2[id]=label
            return hpos2
        


        
    def analyze(self,unique_individuals):
        """
        Gather metrics on a unique set of individuals and their phenotype data
        
        Args:
            unique_individuals (dict): key is indiv_id, with values being phenotype data, and affected status, and project
            
        """
        unique_phenotypes = self.find_unique_phenotypes(unique_individuals)
        print ("number of unique phenotypes (roughly HPOs, very few are from phenotypes lacking HPO terms): %s" % len(unique_phenotypes))
        num_individuals_per_unique_phenotype = self.count_num_individuals_per_unique_phenotype(unique_phenotypes)
        self.gen_stats_on_num_individuals_per_unique_phenotype(num_individuals_per_unique_phenotype)
        self.get_percent_of_affected_individuals_with_at_least_one_phenotype(unique_individuals)
       
    
    def get_percent_of_affected_individuals_with_at_least_one_phenotype(self,unique_individuals):
        """
        Find the % of affected individuals with at least one phenotype
        
        Args:
            unique_individuals (dict): key is indiv_id, values are phenotypes, project, and affected status
        
        Returns:
            (decimal): A percentage of affected individuals with at least 1 HPO term
        """
        total_affected=0
        have_atleast_one_hpo_term=0
        for indiv,data in unique_individuals.iteritems():
            if data['affected_status']=='A' and 'CMG' in data['project']:
                total_affected +=1
                if len(data['phenotype_data'])>0:
                    have_atleast_one_hpo_term += 1     
        print ("total number of affected unique individuals in phenotips: %s" % total_affected)   
        print ("total number of affected unique individuals in phenotips with at least one phenotype: %s" % have_atleast_one_hpo_term)           
        print ("percentage of affected individuals (unique) in phenotips with at least one phenotype:", float(have_atleast_one_hpo_term)/float(total_affected ) * 100, "%")
        
    
    def gen_stats_on_num_individuals_per_unique_phenotype(self,num_individuals_per_unique_phenotype):
        """
        Generate basic stats on a number of individuals to a unique HPO term mapping
        
        Args:
            num_individuals_per_unique_phenotype (dict): key is HPO term, value is # of individuals with that HPO
        
        Returns:
            
        """
        pass
        
        
    def count_num_individuals_per_unique_phenotype(self,unique_phenotypes):
        """
        Count how many individuals have a unique phenotypes
        
        Args:
            unique_phenotypes (dict): a structure that looks like 
            { "hpo": {label:"", "individuals":{indiv_id:affected_status}}}
            
        Returns
            dict: a hpo term to a list of individuals who have it {hpo:[individuals....]}
 
        """
        counts={}
        for hpo,mappings in unique_phenotypes.iteritems():
            counts[hpo]=len(mappings['individuals'])
        return counts
        
        
    def find_unique_phenotypes(self,unique_individuals):
        """
        Find unique HPO terms
        
        Args:
            unique_individuals (dict): individuals mapped to their phenotypes, project, and affected statuses
            
        Returns:
            dict: unique HPO terms mapped to the individuals who have them 
                    { "hpo": {label:"", "individuals":{indiv_id:affected_status}}}
        """
        unique_phenotypes={}
        for indiv,data in unique_individuals.iteritems():
            try:
                for hpo,label in data['phenotype_data'].iteritems():
                    if not unique_phenotypes.has_key(hpo):
                        unique_phenotypes[hpo]={"label":label,"individuals":{indiv:data['affected_status']}}
                    else:
                        if not unique_phenotypes[hpo]['individuals'].has_key(indiv):
                            unique_phenotypes[hpo]['individuals'][indiv]=data['affected_status']
            except Exception as e:
                logger.warn(e)
        return unique_phenotypes
        
        
    def get_hpo_terms(self,phenotype_data):
        """
        Returns the set of HPO terms found in this phenotype collection. For this iteration we are concentrating
        on sections 'features' and 'nonstandard_features'. Since nonstandard_features typically lack a HPO term
        we will use the md5 of the label as a proxy unique ID for now 
        
        Args:
            phenotype_data (JSON): A phenotype collection from an individual
        
        Returns:
            dict: the HPO terms found in this collection
            
        """
        hpo_terms={}
        data={}
        try:
            data = json.loads(phenotype_data)
        except:
            return hpo_terms
        try:
            features = data.get('features',None)
            nonstandard_features = data.get('nonstandard_features',None)
            if features:
                for f in features:
                    hpo_terms[f['id']]= f['label']
            if nonstandard_features:
                for f in nonstandard_features:
                    hpo_terms[hashlib.md5(f['label']).hexdigest()]= f['label']
        except Exception as e:
            logger.warn(e)
        return hpo_terms
            
        
        