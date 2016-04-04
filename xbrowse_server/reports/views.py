from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from xbrowse_server.server_utils import JSONResponse
from xbrowse_server.decorators import log_request
from xbrowse_server.api.utils import get_project_and_family_for_user
from django.shortcuts import get_object_or_404
from xbrowse_server.base.models import Project
from xbrowse_server.base.lookups import get_all_saved_variants_for_project, get_variants_with_notes_for_project, \
    get_variants_by_tag, get_causal_variants_for_project
import itertools
from xbrowse_server.base.models import Project, Individual, Family, FamilyGroup, ProjectCollaborator, ProjectPhenotype, \
    VariantNote, ProjectTag
from xbrowse_server.api.utils import add_extra_info_to_variants_family, add_extra_info_to_variants_project
from xbrowse_server.mall import get_reference
import json
from utilities import fetch_project_individuals_data

@csrf_exempt
@login_required
@log_request('export_individual')
def export_project_individuals(request,project_id):
    '''
      Notes:
      1. ONLY project-authorized user has access to this individual
    '''
    family_data,variant_data,phenotype_entry_counts = fetch_project_individuals_data(project_id)
    return JSONResponse({
            'variant': variant_data,
            'family_data': family_data,
            'phenotype_entry_counts':phenotype_entry_counts
        })
