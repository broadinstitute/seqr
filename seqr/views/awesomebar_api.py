"""API for omni-bar auto-complete and search functionality"""


import collections
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import connection
from django.db.models.functions import Length

from django.views.decorators.http import require_GET
from guardian.shortcuts import get_objects_for_user

from seqr.views.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils import \
    _get_json_for_user, \
    _get_json_for_project, \
    render_with_initial_json, \
    create_json_response
from reference_data.models import GencodeGene
from seqr.models import Project, Family, Individual, LocusList, CAN_VIEW

logger = logging.getLogger(__name__)

MAX_STRING_LENGTH = 100

def _get_matching_projects_and_families(user, query, max_results=5):
    project_permissions_check = family_permissions_check = Q()
    if not user.is_staff:
        projects_can_view = [p.id for p in get_objects_for_user(user, CAN_VIEW, Project)]
        project_permissions_check = Q(id__in=projects_can_view)
        family_permissions_check = Q(project_id__in=projects_can_view)

    matching_projects = Project.objects.filter(
        project_permissions_check & (Q(deprecated_project_id__icontains=query) | Q(name__icontains=query))  # Q(description__icontains=query) | Q(project_category__icontains=query)
    )
    matching_families = Family.objects.filter(
        family_permissions_check & (Q(family_id__icontains=query) | Q(display_name__icontains=query))
    )

    projects_result = []
    for p in matching_projects[:max_results]:
        title = p.name
        projects_result.append({
            'title': title[:MAX_STRING_LENGTH],
            'description': '',  # '('+p.description+')' if p.description else '',
            'href': '/project/'+p.deprecated_project_id,
        })

    projects_result.sort(key=lambda f: len(f.get('title', '')))

    families_result = []
    for f in matching_families[:max_results]:
        title = f.display_name
        families_result.append({
            'title': title[:MAX_STRING_LENGTH],
            'description': '('+f.project.name+')' if f.project else '',
            'href': '/project/'+f.project.deprecated_project_id+'/family/'+f.family_id,
        })

    families_result.sort(key=lambda f: len(f.get('title', '')))

    return projects_result, families_result


def _get_matching_genes(user, query, max_results=5):
    result = []
    matching_genes = GencodeGene.objects.filter(Q(gene_id__icontains=query) | Q(gene_name__icontains=query)).order_by(Length('gene_name').asc())
    for g in matching_genes[:max_results]:
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


@login_required
@require_GET
def awesomebar_autocomplete(request):
    """Accepts HTTP GET request with q=.. url arg, and returns suggestions"""

    query = request.GET.get('q', None)

    results = {}
    if len(query) > 0:
        projects, families = _get_matching_projects_and_families(request.user, query)
        if projects:
            results['projects'] = {'name': 'Projects', 'results': projects}
        if families:
            results['families'] = {'name': 'Families', 'results': families}

        genes = _get_matching_genes(request.user, query)
        if genes:
            results['genes'] = {'name': 'Genes', 'results': genes}

    #from pprint import pprint
    #pprint(results)
    return create_json_response({'matches': results})
