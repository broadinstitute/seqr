from xbrowse_server.base.lookups import get_all_saved_variants_for_project, get_variants_with_notes_for_project, \
    get_variants_by_tag, get_causal_variants_for_project
import itertools
from xbrowse_server.base.models import Project, Individual, Family, FamilyGroup, ProjectCollaborator, ProjectPhenotype, \
    VariantNote, ProjectTag
from xbrowse_server.api.utils import add_extra_info_to_variants_family, add_extra_info_to_variants_project
from xbrowse_server.mall import get_reference
import json
from django.shortcuts import get_object_or_404
from xbrowse_server.phenotips.reporting_utilities import phenotype_entry_metric_for_individual

def fetch_project_individuals_data(project_id):
    '''
      Notes:
      1. ONLY project-authorized user has access to this individual
    '''
    project = get_object_or_404(Project, project_id=project_id)
    variants = get_causal_variants_for_project(project)
    variants = sorted(variants, key=lambda v: (v.extras['family_id'], v.xpos))
    grouped_variants = itertools.groupby(variants, key=lambda v: v.extras['family_id'])
    for family_id, family_variants in grouped_variants:
        family = Family.objects.get(project=project, family_id=family_id)
        family_variants = list(family_variants)
        add_extra_info_to_variants_family(get_reference(), family, family_variants)

    family_data=[v.toJSON() for v in variants]
    variant_data={family.family_id: family.get_json_obj() for family in project.get_families()}

    phenotype_entry_counts = gather_phenotype_data_for_project(project_id,variant_data)

    return family_data,variant_data,phenotype_entry_counts
  
  
  
def gather_phenotype_data_for_project(project_id,variant_data):
  '''
    Gathers all phenotype data for this project by individual
    Inputputs:
    1. A project ID (ex: "1kg")
    Outputs:
    1. A list of dictionaries. Each dict represents a patient. 
      Example: {'eid': u'NA19678', 'num_phenotypes_entered': 0}
  '''
  phenotype_entry_counts={}
  for family_id,variant_data in variant_data.iteritems():
    for ind_data in variant_data['individuals']:
      phenotype_entry_counts[ind_data['indiv_id']] = phenotype_entry_metric_for_individual(ind_data['indiv_id'],project_id)
  return phenotype_entry_counts