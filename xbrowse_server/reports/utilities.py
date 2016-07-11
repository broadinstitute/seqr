from xbrowse_server.base.lookups import get_causal_variants_for_project
import itertools
from xbrowse_server.base.models import Project, Individual, Family
from xbrowse_server.api.utils import add_extra_info_to_variants_family
from xbrowse_server.mall import get_reference
from django.shortcuts import get_object_or_404
from xbrowse_server.phenotips.reporting_utilities import phenotype_entry_metric_for_individual
from xbrowse_server import json_displays
from xbrowse_server.base.models import ANALYSIS_STATUS_CHOICES


def fetch_project_individuals_data(project_id):
    """
    Notes:
      1. ONLY project-authorized user has access to this individual
    """
    project = get_object_or_404(Project, project_id=project_id)
    variants = get_causal_variants_for_project(project)
    variants = sorted(variants, key=lambda v: (v.extras['family_id'], v.xpos))
    grouped_variants = itertools.groupby(variants, key=lambda v: v.extras['family_id'])
    for family_id, family_variants in grouped_variants:
        family = Family.objects.get(project=project, family_id=family_id)
        family_variants = list(family_variants)
        add_extra_info_to_variants_family(get_reference(), family, family_variants)

    family_data = [v.toJSON() for v in variants]
    variant_data = {family.family_id: family.get_json_obj() for family in project.get_families()}

    phenotype_entry_counts = gather_phenotype_data_for_project(project_id, variant_data)

    status_description_map = {}
    for abbrev, details in ANALYSIS_STATUS_CHOICES:
        status_description_map[abbrev] = details[0]
    families_json = json_displays.family_list(project.get_families())
    family_statuses = {}
    for f in families_json:
        family_statuses[f['family_id']] = status_description_map[f['analysis_status']['status']]

    return family_data, variant_data, phenotype_entry_counts, family_statuses


def gather_phenotype_data_for_project(project_id, variant_data):
    """
    Gathers all phenotype data for this project by individual

    Args:
        project_id: A project ID (ex: "1kg")

    Return:
        A dictionary of dictionaries. Each dict represents a patient.
        Example: {'eid': u'NA19678', 'num_phenotypes_entered': 0}
    """
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
