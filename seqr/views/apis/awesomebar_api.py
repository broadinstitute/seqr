"""API that generates auto-complete suggestions for the search bar in the header of seqr pages"""
from __future__ import unicode_literals

import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q, ExpressionWrapper, BooleanField
from django.views.decorators.http import require_GET

from reference_data.models import Omim, HumanPhenotypeOntology
from seqr.utils.gene_utils import get_queried_genes
from seqr.views.utils.json_utils import create_json_response, _to_title_case
from seqr.views.utils.permissions_utils import get_projects_user_can_view
from seqr.models import Project, Family, Individual, AnalysisGroup, ProjectCategory
from settings import API_LOGIN_REQUIRED_URL


logger = logging.getLogger(__name__)

MAX_RESULTS_PER_CATEGORY = 8
MAX_STRING_LENGTH = 100


def _get_matching_objects(query, projects, object_cls, filter_fields, object_fields, get_title, get_href, get_description=None, project_field=None, select_related_project=True):
    """Returns objects that match the given query string, and that the user can view, for the given object criteria.

    Args:
        user: Django user
        query: String typed into the awesomebar
        object_cls: Django model class of the object
        filter_fields: Array of field names to match the query against
        get_title: Function to get the title from an object
        get_href: Function to get the href from an object
        get_description: Optional function to get the description from an object
        project_field: Optional string defining the relationship between the object and parent project
    Returns:
        Sorted list of matches where each match is a dictionary of strings
    """
    if project_field:
        matching_objects = getattr(object_cls, 'objects')
        matching_objects = matching_objects.filter(Q(**{'{}__in'.format(project_field): projects}))
        if select_related_project:
            matching_objects = matching_objects.select_related(project_field)
    else:
        matching_objects = projects

    object_filter = Q()
    for field in filter_fields:
        object_filter |= Q(**{'{}__icontains'.format(field): query})
    matching_objects = matching_objects.filter(object_filter).only('guid', *object_fields).distinct()

    results = [{
        'key': obj.guid,
        'title': get_title(obj)[:MAX_STRING_LENGTH],
        'description': '({})'.format(get_description(obj)) if get_description else '',
        'href': get_href(obj),
    } for obj in matching_objects[:MAX_RESULTS_PER_CATEGORY]]

    results.sort(key=lambda f: len(f.get('title', '')))

    return results


def _get_matching_projects(query, projects):
    return _get_matching_objects(
        query, projects, Project,
        filter_fields=['name'],
        object_fields=['name'],
        get_title=lambda p: p.name,
        get_href=lambda p: '/project/{}/project_page'.format(p.guid),
    )


def _get_matching_families(query, projects):
    return _get_matching_objects(
        query, projects, Family,
        filter_fields=['family_id', 'display_name'],
        object_fields=['family_id', 'display_name', 'project__guid', 'project__name'],
        get_title=lambda f: f.display_name or f.family_id,
        get_href=lambda f: '/project/{}/family_page/{}'.format(f.project.guid, f.guid),
        get_description=lambda f: f.project.name,
        project_field='project')


def _get_matching_analysis_groups(query, projects):
    return _get_matching_objects(
        query, projects, AnalysisGroup,
        filter_fields=['name'],
        object_fields=['name', 'project__guid', 'project__name'],
        get_title=lambda f: f.name,
        get_href=lambda f: '/project/{}/analysis_group/{}'.format(f.project.guid, f.guid),
        get_description=lambda f: f.project.name,
        project_field='project')


def _get_matching_individuals(query, projects):
    return _get_matching_objects(
        query, projects, Individual,
        filter_fields=['individual_id', 'display_name'],
        object_fields=[
            'individual_id', 'display_name', 'family__guid', 'family__display_name', 'family__family_id',
            'family__project__guid', 'family__project__name',
        ],
        get_title=lambda i: i.display_name or i.individual_id,
        get_href=lambda i: '/project/{}/family_page/{}'.format(i.family.project.guid, i.family.guid),
        get_description=lambda i: '{}: family {}'.format(i.family.project.name, (i.family.display_name or i.family.family_id)),
        project_field='family__project')


def _get_matching_project_groups(query, projects):
    return _get_matching_objects(
        query, projects, ProjectCategory,
        filter_fields=['name'],
        object_fields=['name'],
        get_title=lambda p: p.name,
        get_href=lambda p: p.guid,
        project_field='projects',
        select_related_project=False,
    )


def _get_matching_genes(query, projects):
    """Returns genes that match the given query string, and that the user can view.

    Args:
       user: Django user
       query: String typed into the awesomebar
    Returns:
       Sorted list of matches where each match is a dictionary of strings
    """
    result = []
    for g in get_queried_genes(query, MAX_RESULTS_PER_CATEGORY):
        if query.lower() in g['gene_id'].lower():
            title = g['gene_id']
            description = g['gene_symbol']
        else:
            title = g['gene_symbol']
            description = g['gene_id']

        result.append({
            'key': g['gene_id'],
            'title': title,
            'description': '('+description+')' if description else '',
            'href': '/gene_info/'+g['gene_id'],
        })

    return result


def _get_matching_omim(query, projects):
    """Returns OMIM records that match the given query string"""
    records = Omim.objects.filter(
        Q(phenotype_mim_number__icontains=query) | Q(phenotype_description__icontains=query)
    ).filter(phenotype_mim_number__isnull=False).annotate(
        description_start=ExpressionWrapper(Q(phenotype_description__istartswith=query), output_field=BooleanField()),
        mim_number_start=ExpressionWrapper(Q(phenotype_mim_number__istartswith=query), output_field=BooleanField()),
    ).only('phenotype_mim_number', 'phenotype_description').order_by(
        '-description_start', '-mim_number_start', 'phenotype_description').distinct()[:MAX_RESULTS_PER_CATEGORY]
    result = []
    for record in records:
        result.append({
            'key': record.phenotype_mim_number,
            'title': record.phenotype_description,
            'description': '({})'.format(record.phenotype_mim_number) if record.phenotype_mim_number else None,
        })

    return result


def _get_matching_hpo_terms(query, projects):
    """Returns OMIM records that match the given query string"""
    records = HumanPhenotypeOntology.objects.filter(
        Q(hpo_id__icontains=query) | Q(name__icontains=query)
    ).annotate(
        name_start=ExpressionWrapper(Q(name__istartswith=query), output_field=BooleanField()),
        hpo_id_start=ExpressionWrapper(Q(hpo_id__istartswith=query), output_field=BooleanField()),
    ).only('hpo_id', 'name', 'category_id').order_by(
        '-name_start', '-hpo_id_start', 'name').distinct()[:MAX_RESULTS_PER_CATEGORY]
    result = []
    for record in records:
        result.append({
            'key': record.hpo_id,
            'title': record.name,
            'description': '({})'.format(record.hpo_id),
            'category': record.category_id,
        })

    return result


CATEGORY_MAP = {
    'genes': _get_matching_genes,
    'omim': _get_matching_omim,
    'hpo_terms': _get_matching_hpo_terms,
}
PROJECT_SPECIFIC_CATEGORY_MAP = {
    'projects': _get_matching_projects,
    'families': _get_matching_families,
    'analysis_groups': _get_matching_analysis_groups,
    'individuals': _get_matching_individuals,
    'project_groups': _get_matching_project_groups,
}
CATEGORY_MAP.update(PROJECT_SPECIFIC_CATEGORY_MAP)
DEFAULT_CATEGORIES = ['projects', 'families', 'analysis_groups', 'individuals', 'genes']


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@require_GET
def awesomebar_autocomplete_handler(request):
    """Accepts HTTP GET request with q=.. url arg, and returns suggestions"""

    query = request.GET.get('q')
    if query is None:
        raise ValueError("missing ?q=<prefix> url arg")
    if not query:
        return create_json_response({'matches': {}})

    categories = request.GET.get('categories').split(',') if request.GET.get('categories') else DEFAULT_CATEGORIES

    projects = get_projects_user_can_view(request.user) if any(
        category for category in categories if category in PROJECT_SPECIFIC_CATEGORY_MAP) else None

    results = {
        category: {'name': _to_title_case(category), 'results': CATEGORY_MAP[category](query, projects)}
        for category in categories
    }

    return create_json_response({'matches': {k: v for k, v in results.items() if v['results']}})
