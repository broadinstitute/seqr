import json

from django.core import urlresolvers
from django.db.models import Prefetch
from django.utils.http import urlquote

from xbrowse_server.base.models import Project, Family, Individual
from xbrowse_server.mall import get_project_datastore
from xbrowse import constants
from xbrowse import inheritance as x_inheritance


def get_browse_link(project_id, family_id, search_query=None, inheritance_slug=None, inheritance=None): 
    """
    Return a direct link to the browser for project/family, with optional autofill options
    Obviously should not have an inheritance and inheritance_slug
    """
    base_url = urlresolvers.reverse('mendelian_variant_search', args=[project_id, family_id]) + '?'

    if search_query is not None: 
        # TODO: switch to better search_profile object
        search_profile = {
            'variantQuery': search_query, 
        }
        base_url += '&load_search_profile=' + urlquote(json.dumps(search_profile))

    if inheritance is not None: 
        base_url += '&load_inheritance=' + urlquote(json.dumps(inheritance))

    if inheritance_slug is not None: 
        base_url += '&load_inheritance_slug=' + urlquote(inheritance_slug)

    return base_url

def get_project_and_family(project_id, family_id): 
    """ 
    Return (project, family) tuple of django objects
    Raises ObjectDoesNotExist if invalid
    """
    project = Project.objects.get(project_id=project_id)
    family = Family.objects.get(project=project, family_id=family_id)

    return project, family

def get_inheritances(family): 

    return x_inheritance.get_family_inheritances(family)

def get_projects_for_user(user):

    if user.is_staff: 
        return Project.objects.all().order_by('project_id')
    else: 
        return [p for p in Project.objects.all().order_by('project_id') if p.can_view(user)]


def get_loaded_projects_for_user(user, fields=None):
    projects = Project.objects.all()
    if not user.is_staff:
        projects = projects.filter(projectcollaborator__user=user)
    if fields:
        projects = projects.only(*fields)

    mongo_projects = projects.filter(vcffile__elasticsearch_index=None).distinct()
    mongo_projects = filter(
        lambda p: get_project_datastore(p, datastore_type='mongo').project_collection_is_loaded(p), mongo_projects
    )
    es_projects = list(projects.exclude(vcffile__elasticsearch_index=None))
    return mongo_projects + es_projects


def get_collaborators_for_user(user):

    projs = [p for p in get_projects_for_user(user) if not p.is_public]
    collabs = list({c for project in projs for c in project.get_collaborators()})
    return collabs

def get_families_for_user(user):

    if user.is_staff: 
        return Family.objects.all()
    else: 
        # TODO: need to consider groups here, too. 
        return [f for f in Family.objects.all() if f.can_view(user)]


def get_filtered_families(filters, fields):
    return list(Family.objects.filter(**filters).only(*fields).prefetch_related(
        Prefetch('individual_set', queryset=Individual.objects.prefetch_related('vcf_files').only(*Individual.INDIVIDUAL_JSON_FIELDS_NO_IDS))
    ))


VARIANT_QUERY_DEFAULTS_NAMES = {
    'high_impact': 'High impact',
    'moderate_impact': 'Moderate or greater impact',
    'all_coding': 'All coding and splice', 
}

VARIANT_QUERY_DEFAULTS_DESCRIPTIONS = {
    'high_impact': 'SNPs with a high likelihood of having a significant impact if function is disrupted.',
    'moderate_impact': 'SNPs with a high likelihood of having a moderate or significant impact',
    'all_coding': 'All coding and extended splice variants'
}

def get_variant_query_defaults(): 

    defaults = {}
    for key, value in constants.QUERY_DEFAULTS.items(): 
        defaults[key] = {
            'name': VARIANT_QUERY_DEFAULTS_NAMES[key], 
            'description': VARIANT_QUERY_DEFAULTS_DESCRIPTIONS[key], 
            'query': value, 
        }
    return defaults

def get_families_from_params(params): 
    pass

