import json
import requests

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from seqr.models import Project, _slugify,  CAN_VIEW
from seqr.views.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.json_utils import create_json_response


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def query_variants(request, project_guid):
    """Search variants

    Args:
        project_guid (string): GUID of the project to query

    HTTP POST
        Response body - will be json with the delete projectGuid mapped to the special 'DELETE' keyword:
            {
                'projectsByGuid':  { <projectGuid1> : 'DELETE' }
            }

    """

    project = Project.objects.get(guid=project_guid)

    # check permissions
    if not request.user.has_perm(CAN_VIEW, project) and not request.user.is_staff:
        raise PermissionDenied


    request_json = json.loads(request.body)
    #if 'form' not in request_json:
    #    return create_json_response({}, status=400, reason="Invalid request: 'form' not in request_json")


    results = requests.post('http://localhost:6060/', json={
        "page": 1,
        "limit": 100,
        "genotype_filters": {
            "1877nih": { "num_alt": 1 },
            "22067nih": { "num_alt": 2 }
        }
    })


    print(results.status_code)

    results = json.loads(results.text)

    # TODO delete Family, Individual, and other objects under this project
    return create_json_response({
        'variants': results,
    })
