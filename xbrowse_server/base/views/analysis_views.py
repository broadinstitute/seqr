import json
import sys

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

from xbrowse_server.decorators import log_request
from xbrowse_server.base.models import Project, Family, Cohort
from xbrowse import inheritance as x_inheritance
from xbrowse_server.mall import get_project_datastore

@login_required
@log_request('mendelian_variant_search')
def mendelian_variant_search(request, project_id, family_id):

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    if not family.has_data('variation'):
        return render(request, 'analysis_unavailable.html', {
            'reason': 'This family does not have any variant data.'
        })

    has_gene_search = get_project_datastore(project_id).project_collection_is_loaded(project_id)
    sys.stderr.write("Running mendelian_variant_search on %(project_id)s %(family_id)s. has_gene_search = %(has_gene_search)s\n " % locals() )
    return render(request, 'mendelian_variant_search.html', {
        'project': project, 
        'family': family,
        'family_genotype_filters_json': json.dumps(x_inheritance.get_genotype_filters(family.xfamily())),
        'has_gene_search': has_gene_search
    })


@login_required
@log_request('cohort_variant_search')
def cohort_variant_search(request, project_id, cohort_id):

    project = get_object_or_404(Project, project_id=project_id)
    cohort = get_object_or_404(Cohort, project=project, cohort_id=cohort_id)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    return render(request, 'cohort/cohort_variant_search.html', {
        'project': project,
        'cohort': cohort,
        'family_genotype_filters_json': json.dumps(x_inheritance.get_genotype_filters(cohort.xfamily())),
    })

@login_required
@log_request('cohort_gene_search')
def cohort_gene_search(request, project_id, cohort_id):

    project = get_object_or_404(Project, project_id=project_id)
    cohort = get_object_or_404(Cohort, project=project, cohort_id=cohort_id)
    if not project.can_view(request.user):
        return HttpResponse('unauthorized')

    return render(request, 'cohort/cohort_gene_search.html', {
        'project': project, 
        'cohort': cohort,
    })

