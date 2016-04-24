"""

This file contains a bunch of methods for transforming server objects to JSON that can be rendered to client
For example, turn a list of base.Family instances into JSON with relevant fields
These JSON objects are used by client javascript and by django templates

"""
from django.core.urlresolvers import reverse
from django.conf import settings


def individual_list(_individual_list):
    individual_d_list = []
    for indiv in _individual_list:
        project_id = indiv.project.project_id
        family_id = indiv.get_family_id()
        individual_d_list.append({
            'indiv_id': indiv.indiv_id,
            'nickname': indiv.nickname,
            'family_id': family_id,
            'family_url': (reverse('family_home', args=(project_id, family_id) ) if family_id else None),
            'project_id': project_id,
            'maternal_id': indiv.maternal_id,
            'paternal_id': indiv.paternal_id,
            'gender': indiv.gender,
            'affected_status': indiv.affected,
            'phenotypes': [{'slug': ipheno.slug(), 'value': ipheno.val()} for ipheno in indiv.get_phenotypes() if ipheno.val() is not None],
            'data': indiv.data(),
        })
    return individual_d_list


def family_list(_family_list):
    family_d_list = []
    for family in _family_list:
        family_d_list.append({
            'url': reverse('family_home', args=(family.project.project_id, family.family_id)),
            'family_id': family.family_id,
            'family_name': family.family_name,
            'data_status': family.get_data_status(),
            'project_id': family.project.project_id,
            'num_individuals': family.num_individuals(),
            'num_causal_variants': family.num_causal_variants(),
            'short_description': family.short_description,
            'analysis_status' : family.get_analysis_status_json(),
            'pedigree_image_url': family.pedigree_image.url if family.pedigree_image else None,            
            'phenotypes': [p.slug for p in family.get_phenotypes()],
        })
    return family_d_list