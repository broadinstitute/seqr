from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from xbrowse_server.server_utils import JSONResponse
from xbrowse_server.decorators import log_request
from utilities import fetch_project_individuals_data
#from utilities import fetch_project_single_individual_data


@csrf_exempt
@login_required
@log_request('export_individuals')
def export_project_individuals(request, project_id):
    '''
      Notes:
      1. ONLY project-authorized user has access to this individual
    '''
    family_data, variant_data, phenotype_entry_counts, family_statuses = fetch_project_individuals_data(project_id)
    return JSONResponse({
            'variant': variant_data,
            'family_data': family_data,
            'phenotype_entry_counts':phenotype_entry_counts
        })
    