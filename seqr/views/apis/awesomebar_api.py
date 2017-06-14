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
from reference_data.models import GencodeGene
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
    project_permissions_check = Q()
    if not user.is_staff:
        projects_can_view = [p.id for p in get_objects_for_user(user, CAN_VIEW, Project)]
        project_permissions_check = Q(id__in=projects_can_view)

    matching_projects = Project.objects.filter(
        project_permissions_check & (
            Q(deprecated_project_id__icontains=query) |
            Q(name__icontains=query)
        )  # Q(description__icontains=query) | Q(project_category__icontains=query)
    )

    projects_result = []
    for p in matching_projects[:MAX_RESULTS_PER_CATEGORY]:
        title = p.name or p.guid  # TODO make sure all projects & families have a name
        projects_result.append({
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
    family_permissions_check = Q()
    if not user.is_staff:
        projects_can_view = [p.id for p in get_objects_for_user(user, CAN_VIEW, Project)]
        family_permissions_check = Q(project__id__in=projects_can_view)

    matching_families = Family.objects.select_related('project').filter(
        family_permissions_check & (Q(family_id__icontains=query) | Q(display_name__icontains=query))
    )

    families_result = []
    for f in matching_families[:MAX_RESULTS_PER_CATEGORY]:
        title = f.display_name or f.family_id or f.guid
        families_result.append({
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
    individual_permissions_check = Q()
    if not user.is_staff:
        projects_can_view = [p.id for p in get_objects_for_user(user, CAN_VIEW, Project)]
        individual_permissions_check = Q(family__project__id__in=projects_can_view)

    matching_individuals = Individual.objects.select_related('family__project').filter(
        individual_permissions_check & (Q(individual_id__icontains=query) | Q(display_name__icontains=query))
    )

    individuals_result = []
    for i in matching_individuals[:MAX_RESULTS_PER_CATEGORY]:
        title = i.display_name or i.individual_id or i.guid
        f = i.family
        individuals_result.append({
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
    matching_genes = GencodeGene.objects.filter(Q(gene_id__icontains=query) | Q(gene_name__icontains=query)).order_by(Length('gene_name').asc())
    for g in matching_genes[:MAX_RESULTS_PER_CATEGORY]:
        if query.lower() in g.gene_id.lower():
            title = g.gene_id
            description = g.gene_name
        else:
            title = g.gene_name
            description = g.gene_id

        result.append({
            'title': title,
            'description': '('+description+')' if description else '',
            'href': '/gene/'+g.gene_id,
        })

    return result


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@require_GET
def awesomebar_autocomplete(request):
    """Accepts HTTP GET request with q=.. url arg, and returns suggestions"""

    query = request.GET.get('q')
    if query is None:
        raise ValueError("missing ?q=<prefix> url arg")

    results = collections.OrderedDict()
    if len(query) > 0:
        projects = _get_matching_projects(request.user, query)
        if projects:
            results['projects'] = {'name': 'Projects', 'results': projects}

        families = _get_matching_families(request.user, query)
        if families:
            results['families'] = {'name': 'Families', 'results': families}

        individuals = _get_matching_individuals(request.user, query)
        if individuals:
            results['individuals'] = {'name': 'Individuals', 'results': individuals}

        genes = _get_matching_genes(request.user, query)
        if genes:
            results['genes'] = {'name': 'Genes', 'results': genes}


    return create_json_response({'matches': results})
