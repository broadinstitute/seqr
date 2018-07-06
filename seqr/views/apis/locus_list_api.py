import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from seqr.models import LocusList
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import get_json_for_locus_lists


logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def locus_lists(request):
    locus_lists = get_json_for_locus_lists(LocusList.objects.filter(Q(is_public=True) | Q(created_by=request.user)))

    return create_json_response({locus_list['locusListGuid']: locus_list for locus_list in locus_lists})