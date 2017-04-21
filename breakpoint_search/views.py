from collections import Counter, OrderedDict
import sys
import json
import settings
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse


from xbrowse_server.decorators import log_request
from xbrowse_server.mall import get_reference 
from django.conf import settings
from django.core.exceptions import PermissionDenied

import logging
import os
from breakpoint_search.models import Breakpoint, BreakpointMetaData

log = logging.getLogger('xbrowse_server')


from xbrowse_server.base.models import Project, Family, ANALYSIS_STATUS_CHOICES,\
    Individual

@login_required
@log_request('breakpoint_search')
def breakpoints(request, project_id, family_id):

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id) 

    min_sample_obs = int(request.GET.get('obs','0'))
    max_sample_count = int(request.GET.get('samples',str(sys.maxint)))

    log.info("Fetching breakpoints with obs>=%d and samples <= %d for project %s, family %s", 
            min_sample_obs, max_sample_count, project_id, family_id)

    affected_indiv_ids = [i.indiv_id for i in family.get_individuals() if i.affected == 'A']

    log.info("Affected individuals in %s are %s", family_id, ','.join(affected_indiv_ids))

    bps = Breakpoint.objects.filter(project=project, 
                                 individual__indiv_id__in=affected_indiv_ids,
                                 sample_count__lte=max_sample_count,
                                 obs__gte=min_sample_obs)

    breakpoint_metadatas = BreakpointMetaData.objects.filter(
            breakpoint__individual__indiv_id__in=affected_indiv_ids,
            breakpoint__project=project,
            breakpoint__sample_count__lte=max_sample_count,
            breakpoint__obs__gte=min_sample_obs
            )

    log.info("Retrieved %d applicable metadatas", len(breakpoint_metadatas))

    metadatas = dict([(bpm.breakpoint.xpos, bpm.toDict()) for bpm in breakpoint_metadatas])

    log.info("Breakpoint search found %d breakpoints", len(bps))
    
    return HttpResponse(json.dumps(
        {
            'breakpoints': [ bp.toList() for bp in bps.all() ],
            'metadatas' : metadatas
        }), content_type='application/json')

@login_required
@log_request('breakpoint_search')
def breakpoint_search(request, project_id, family_id):

    log.info("Showing main breakpoint search page")

    project = get_object_or_404(Project, project_id=project_id)
    family = get_object_or_404(Family, project=project, family_id=family_id)
    if not project.can_view(request.user):
        raise PermissionDenied

    if not family.has_data('breakpoints'):
        return render(request, 'analysis_unavailable.html', {
            'reason': 'This family does not have any breakpoint data.'
        })

    gene_lists = project.get_gene_list_map()

    gene_list_json = dict([ (get_reference().get_gene_symbol(g),[ gl.name for gl in gll ]) for g,gll in gene_lists.iteritems() ])

    bam_file_paths = dict((ind.indiv_id, os.path.join(settings.READ_VIZ_BAM_PATH,ind.bam_file_path)) for ind in family.get_individuals())

    return render(request, 'breakpoint_search.html', {
        'project': project,
        'family': family,
        'gene_lists_json': json.dumps(gene_list_json),
        'bam_files_json': json.dumps(bam_file_paths),
    })
    
    
@login_required
def project_breakpoint(request, project_id, breakpoint_id):
    """
    Retrieve details or update a breakpoint
    """
    if request.method == 'POST':
        log.info("Updating breakpoint %s for project %s", breakpoint_id, project_id)

        project = get_object_or_404(Project, project_id=project_id)
        individual = get_object_or_404(Individual, project=project, indiv_id=request.POST['indiv_id'])
        if individual.project.id != project.id:
            raise Exception("Individual specified is not part of project %s" % project.project_name)

        breakpoint = Breakpoint.objects.get(xpos=breakpoint_id, 
                                            project=project,
                                            individual=individual)

        meta = BreakpointMetaData()
        meta.breakpoint = breakpoint
        meta.type = request.POST['type']
        meta.tags = request.POST.get('tags','')
        meta.comment = request.POST.get('comment','')
        meta.save()
        
        return HttpResponse(json.dumps(
        {
            'status': 'ok'
        }), content_type='application/json') 
        return render()
    else:
        raise Exception("Not supported yet")
 
    