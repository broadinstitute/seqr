"""API that generates auto-complete suggestions for the search bar in the header of seqr pages"""

import collections
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models.functions import Length

from django.views.decorators.http import require_GET

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response, _to_title_case
from reference_data.models import GeneInfo
from seqr.models import Project, Family, Individual, AnalysisGroup

logger = logging.getLogger(__name__)

MAX_RESULTS_PER_CATEGORY = 8
MAX_STRING_LENGTH = 100


def _get_matching_objects(user, query, object_cls, filter_fields, get_title, get_href, get_description=None, project_field=''):
    """Returns objects that match the given query string, and that the user can view, for the given object criteria.

    Args:
        user: Django user
        query: String typed into the awesomebar
    Returns:
        Sorted list of matches where each match is a dictionary of strings
    """
    project_field_prefix = '{}__'.format(project_field) if project_field else ''
    object_filter = Q()
    for field in filter_fields:
        object_filter |= Q(**{'{}__icontains'.format(field): query})
    if not user.is_superuser:
        if user.is_staff:
            object_filter &= Q(**{'{}can_view_group__user'.format(project_field_prefix): user}) | Q(**{'{}disable_staff_access'.format(project_field_prefix): False})
        else:
            object_filter &= Q(**{'{}can_view_group__user'.format(project_field_prefix): user})

    matching_objects = getattr(object_cls, 'objects').filter(object_filter).distinct()
    if project_field:
        matching_objects = matching_objects.select_related(project_field)

    results = [{
        'key': obj.guid,
        'title': get_title(obj)[:MAX_STRING_LENGTH],
        'description': u'({})'.format(get_description(obj)) if get_description else '',
        'href': get_href(obj),
    } for obj in matching_objects[:MAX_RESULTS_PER_CATEGORY]]

    results.sort(key=lambda f: len(f.get('title', '')))

    return results


def _get_matching_projects(user, query):
    return _get_matching_objects(
        user, query, Project,
        filter_fields=['deprecated_project_id', 'name'],
        get_title=lambda p: p.name,
        get_href=lambda p: '/project/{}/project_page'.format(p.guid),
    )


def _get_matching_families(user, query):
    return _get_matching_objects(
        user, query, Family,
        filter_fields=['family_id', 'display_name'],
        get_title=lambda f: f.display_name or f.family_id,
        get_href=lambda f: '/project/{}/family_page/{}'.format(f.project.guid, f.guid),
        get_description=lambda f: f.project.name,
        project_field='project')


def _get_matching_analysis_groups(user, query):
    return _get_matching_objects(
        user, query, AnalysisGroup,
        filter_fields=['name'],
        get_title=lambda f: f.name,
        get_href=lambda f: '/project/{}/analysis_group/{}'.format(f.project.guid, f.guid),
        get_description=lambda f: f.project.name,
        project_field='project')


def _get_matching_individuals(user, query):
    return _get_matching_objects(
        user, query, Individual,
        filter_fields=['individual_id', 'display_name'],
        get_title=lambda i: i.display_name or i.individual_id,
        get_href=lambda i: '/project/{}/family_page/{}'.format(i.family.project.guid, i.family.guid),
        get_description=lambda i: '{}: family {}'.format(i.family.project.name, (i.family.display_name or i.family.family_id)),
        project_field='family__project')


def _get_matching_genes(user, query):
    """Returns genes that match the given query string, and that the user can view.

    Args:
       user: Django user
       query: String typed into the awesomebar
    Returns:
       Sorted list of matches where each match is a dictionary of strings
    """
    result = []
    matching_genes = GeneInfo.objects.filter(Q(gene_id__icontains=query) | Q(gene_symbol__icontains=query)).only(
        'gene_id', 'gene_symbol').order_by(Length('gene_symbol').asc()).distinct()
    for g in matching_genes[:MAX_RESULTS_PER_CATEGORY]:
        if query.lower() in g.gene_id.lower():
            title = g.gene_id
            description = g.gene_name
        else:
            title = g.gene_name
            description = g.gene_id

        result.append({
            'key': g.gene_id,
            'title': title,
            'description': '('+description+')' if description else '',
            'href': '/gene_info/'+g.gene_id,
        })

    return result


CATEGORY_MAP = {
    'projects': _get_matching_projects,
    'families': _get_matching_families,
    'analysis_groups': _get_matching_analysis_groups,
    'individuals': _get_matching_individuals,
    'genes': _get_matching_genes,
}


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@require_GET
def awesomebar_autocomplete_handler(request):
    """Accepts HTTP GET request with q=.. url arg, and returns suggestions"""

    query = request.GET.get('q')
    if query is None:
        raise ValueError("missing ?q=<prefix> url arg")

    categories = request.GET.get('categories').split(',') if request.GET.get('categories') else CATEGORY_MAP.keys()

    results = {
        category: {'name': _to_title_case(category), 'results': CATEGORY_MAP[category](request.user, query)}
        for category in categories
    }

    return create_json_response({'matches': {k: v for k, v in results.items() if v['results']}})
