from xbrowse_server.base.lookups import get_causal_variants_for_project
import itertools
from xbrowse_server.base.models import Project, Individual, Family
from xbrowse_server.api.utils import add_extra_info_to_variants_family
from xbrowse_server.mall import get_reference
from django.shortcuts import get_object_or_404
from xbrowse_server.phenotips.reporting_utilities import phenotype_entry_metric_for_individual
from xbrowse_server import json_displays
from xbrowse_server.base.models import ANALYSIS_STATUS_CHOICES
from xbrowse_server.base.models import VariantTag
from xbrowse_server.base.models import ProjectTag
from xbrowse_server.mall import get_datastore


def fetch_project_individuals_data(project_id):
    """
    Notes:
      1. ONLY project-authorized user has access to this individual
    """
    project = get_object_or_404(Project, project_id=project_id)
    
    project_tag = ProjectTag.objects.filter(project__project_id='1kg')
    variant_tags = VariantTag.objects.filter(project_tag=project_tag)
    
    variants=[]
    for variant_tag in variant_tags:        
        variant = get_datastore(project.project_id).get_single_variant(
                project.project_id,
                variant_tag.toJSON()['family'],
                variant_tag.xpos,
                variant_tag.ref,
                variant_tag.alt,
        )
        if variant is None:
            raise ValueError("Variant no longer called in this family (did the callset version change?)")
        variants.append(variant.toJSON())
    return variants,{}

  

'''
def gather_phenotype_data_for_project(project_id,variant_data):
    
    Gathers all phenotype data for this project by individual

    Args:
        project_id: A project ID (ex: "1kg")

    Return:
        A dictionary of dictionaries. Each dict represents a patient.
        Example: {'eid': u'NA19678', 'num_phenotypes_entered': 0}
  
    phenotype_entry_counts = {}
    for family_id, variant_data in variant_data.iteritems():
        for ind_data in variant_data['individuals']:
            individual = Individual.objects.get(project__project_id=project_id, indiv_id=ind_data['indiv_id'])
            external_id = individual.phenotips_id
            phenotype_metrics = phenotype_entry_metric_for_individual(project_id, external_id)
            phenotype_entry_counts[ind_data['indiv_id']] = {
                "count": phenotype_metrics['phenotype_count'],
                "clinicalStatus": phenotype_metrics['clinicalStatus'],
                "family_id": family_id
            }
    return phenotype_entry_counts
'''