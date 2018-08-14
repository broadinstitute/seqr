"""API that generates auto-complete suggestions for the search bar in the header of seqr pages"""

import collections
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models.functions import Length

from django.views.decorators.http import require_GET
from guardian.shortcuts import get_objects_for_user

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from reference_data.models import GeneInfo
from seqr.models import Project, Family, Individual, CAN_VIEW

logger = logging.getLogger(__name__)

MAX_RESULTS_PER_CATEGORY = 8
MAX_STRING_LENGTH = 100


def _get_matching_projects(user, query):
    """Returns projects that match the given query string, and that the user can view.

    Args:
        user: Django user
        query: String typed into the awesomebar
    Returns:
        Sorted list of matches where each match is a dictionary of strings
    """
    project_filter = Q(deprecated_project_id__icontains=query) | Q(name__icontains=query)
    if not user.is_superuser:
        if user.is_staff:
            project_filter &= Q(can_view_group__user=user) | Q(disable_staff_access=False)
        else:
            project_filter &= Q(can_view_group__user=user)

    matching_projects = Project.objects.filter(project_filter).distinct()

    projects_result = []
    for p in matching_projects[:MAX_RESULTS_PER_CATEGORY]:
        title = p.name or p.guid  # TODO make sure all projects & families have a name
        projects_result.append({
            'key': p.guid,
            'title': title[:MAX_STRING_LENGTH],
            'description': '',  # '('+p.description+')' if p.description else '',
            'href': '/project/%s/project_page' % p.guid,
        })

    projects_result.sort(key=lambda f: len(f.get('title', '')))

    return projects_result


def _get_matching_families(user, query):
    """Returns families that match the given query string, and that the user can view.

    Args:
        user: Django user
        query: String typed into the awesomebar
    Returns:
        Sorted list of matches where each match is a dictionary of strings
    """
    family_filter = Q(family_id__icontains=query) | Q(display_name__icontains=query)
    if not user.is_superuser:
        if user.is_staff:
            family_filter &= Q(project__can_view_group__user=user) | Q(project__disable_staff_access=False)
        else:
            family_filter &= Q(project__can_view_group__user=user)

    matching_families = Family.objects.select_related('project').filter(family_filter).distinct()

    families_result = []
    for f in matching_families[:MAX_RESULTS_PER_CATEGORY]:
        title = f.display_name or f.family_id or f.guid
        families_result.append({
            'key': f.guid,
            'title': title[:MAX_STRING_LENGTH],
            'description': ('(%s)' % f.project.name) if f.project else '',
            'href': '/project/'+f.project.deprecated_project_id+'/family/'+f.family_id,
        })

    families_result.sort(key=lambda f: len(f.get('title', '')))

    return families_result


def _get_matching_individuals(user, query):
    """Returns individuals that match the given query string, and that the user can view.

    Args:
        user: Django user
        query: String typed into the awesomebar
    Returns:
        Sorted list of matches where each match is a dictionary of strings
    """
    individual_filter = Q(individual_id__icontains=query) | Q(display_name__icontains=query)
    if not user.is_superuser:
        if user.is_staff:
            individual_filter &= Q(family__project__can_view_group__user=user) | Q(family__project__disable_staff_access=False)
        else:
            individual_filter &= Q(family__project__can_view_group__user=user)

    matching_individuals = Individual.objects.select_related('family__project').filter(individual_filter).distinct()

    individuals_result = []
    for i in matching_individuals[:MAX_RESULTS_PER_CATEGORY]:
        title = i.display_name or i.individual_id or i.guid
        f = i.family
        individuals_result.append({
            'key': i.guid,
            'title': title[:MAX_STRING_LENGTH],
            'description': ('(%s : family %s)' % (f.project.name, f.display_name)) if f.project else '',
            'href': '/project/'+f.project.deprecated_project_id+'/family/'+f.family_id,
        })

    individuals_result.sort(key=lambda i: len(i.get('title', '')))

    return individuals_result


def _get_matching_genes(user, query):
    """Returns genes that match the given query string, and that the user can view.

    Args:
       user: Django user
       query: String typed into the awesomebar
    Returns:
       Sorted list of matches where each match is a dictionary of strings
    """
    result = []
    matching_genes = GeneInfo.objects.filter(Q(gene_id__icontains=query) | Q(gene_name__icontains=query)).only(
        'gene_id', 'gene_name').order_by(Length('gene_name').asc()).distinct()
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


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@require_GET
def awesomebar_autocomplete_handler(request):
    """Accepts HTTP GET request with q=.. url arg, and returns suggestions"""

    query = request.GET.get('q')
    if query is None:
        raise ValueError("missing ?q=<prefix> url arg")

    categories = request.GET.get('categories', '').split(',')

    results = collections.OrderedDict()
    if len(query) > 0:
        projects = _get_matching_projects(request.user, query) if 'projects' in categories else None
        if projects:
            results['projects'] = {'name': 'Projects', 'results': projects}

        families = _get_matching_families(request.user, query) if 'families' in categories else None
        if families:
            results['families'] = {'name': 'Families', 'results': families}

        individuals = _get_matching_individuals(request.user, query) if 'individuals' in categories else None
        if individuals:
            results['individuals'] = {'name': 'Individuals', 'results': individuals}

        genes = _get_matching_genes(request.user, query) if 'genes' in categories else None
        if genes:
            results['genes'] = {'name': 'Genes', 'results': genes}


    return create_json_response({'matches': results})
