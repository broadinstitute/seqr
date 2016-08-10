#from xbrowse_server.base.lookups import get_causal_variants_for_project
#import itertools
#from xbrowse_server.base.models import Project, Individual, Family
#from xbrowse_server.api.utils import add_extra_info_to_variants_family
#from xbrowse_server.mall import get_reference
#from django.shortcuts import get_object_or_404
#from xbrowse_server.phenotips.reporting_utilities import phenotype_entry_metric_for_individual
#from xbrowse_server import json_displays
#from xbrowse_server.base.models import ANALYSIS_STATUS_CHOICES
#from xbrowse_server.base.models import VariantTag
#from xbrowse_server.base.models import ProjectTag
#from xbrowse_server.mall import get_datastore


#####
#####
##DEPRACATION CANDIDATE
#####
#####
#def fetch_project_individuals_data(project_id):
#    """
#    Notes:
#      1. ONLY project-authorized user has access to this individual
#    """
#    project = get_object_or_404(Project, project_id=project_id)
#    
#    project_tag = ProjectTag.objects.filter(project__project_id='1kg')
#    variant_tags = VariantTag.objects.filter(project_tag=project_tag)
#    
#    variants=[]
#    for variant_tag in variant_tags:        
##        variant = get_datastore(project.project_id).get_single_variant(
#               project.project_id,
##               variant_tag.toJSON()['family'],
#                variant_tag.xpos,
#                variant_tag.ref,
#                variant_tag.alt,
#        )
#        if variant is None:
#            raise ValueError("Variant no longer called in this family (did the callset version change?)")
#        variants.append(variant.toJSON())
#    return variants,{}

  
