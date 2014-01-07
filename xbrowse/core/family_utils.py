"""

Structure of a family is: 

{
    project_id
    family_id
    coll_name 
    vcf_file

    individuals: 
        indiv_id -> {individual}

}

Where an individual contains: 
{
    indiv_id 
    has_exome (true/false)
    paternal_id (string, '.' if unknown)
    maternal_id (string, '.' if unknown)
    affected (true/false)
    sex ("1" or "2", 2 is female) 
}

A family is uniquely identified by (project_id, family_id) tuple
An indiv_id need only be unique within a family

project_id is required, but it only has to exist; no analyses actually refer to project at a low level; 
it's just for organizing similar samples

If you set project_id to '.' for all families, then family_id is a unique id by default

This code is all meant to be readable, not fast. We may need to refactor if it gets CPU-intense

"""

import copy


# REMOVE
_INDIV_DEFAULTS = {
    'family_id': '.', 
    'has_exome': True, 
    'paternal_id': '.', 
    'maternal_id': '.', 
    'affected': 'N',
    'sex': '1', 
}

def make_indiv(indiv_id, **kwargs): 
    """
    Default indiv is unaffected male with an exome, with no parents
    TODO: validation
    """
    ret = { 'indiv_id': indiv_id }
    for k,v in _INDIV_DEFAULTS.items(): 
        ret[k] = kwargs.get(k, v)
    return ret

_FAMILY_DEFAULTS = {
    'project_id': '.',
    'individuals': {}, 
    'coll_name': '.', 
}

def make_family(project_id, family_id): 
    """
    TODO: kwargs like make_indiv
    ...and then validation
    """
    ret = copy.deepcopy(_FAMILY_DEFAULTS)
    ret['project_id'] = project_id
    ret['family_id'] = family_id
    return ret

def get_indiv_ids_for_family_set(family_set): 
    """
    Return list of indiv_ids for all indivs in family_set 
    """
    all_indivs = []
    for family in family_set: 
        all_indivs.extend(family['individuals'].keys())
    return all_indivs



