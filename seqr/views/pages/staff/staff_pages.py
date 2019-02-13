import logging

from collections import defaultdict
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from requests.exceptions import ConnectionError

from seqr.models import Sample, Family, Individual
from seqr.views.utils.proxy_request_utils import proxy_request
from settings import LOGIN_URL, KIBANA_SERVER

logger = logging.getLogger(__name__)


@staff_member_required(login_url=LOGIN_URL)
def seqr_stats_page(request):

    families_count = Family.objects.only('family_id').distinct('family_id').count()
    individuals_count = Individual.objects.only('individual_id').distinct('individual_id').count()

    sample_counts = defaultdict(set)
    for sample in Sample.objects.filter(sample_status=Sample.SAMPLE_STATUS_LOADED).only('sample_id', 'sample_type'):
        sample_counts[sample.sample_type].add(sample.sample_id)

    for sample_type, sample_ids_set in sample_counts.items():
        sample_counts[sample_type] = len(sample_ids_set)

    return render(request, "staff/seqr_stats.html", {
        'families_count': families_count,
        'individuals_count': individuals_count,
        'sample_counts': sample_counts,
    })


@staff_member_required(login_url=LOGIN_URL)
def users_page(request):

    return render(request, "staff/users_table.html", {
        'users': User.objects.all().order_by('email')
    })

@staff_member_required(login_url=LOGIN_URL)
def kibana_page(request):

    return render(request, "staff/kibana_page.html")

@staff_member_required(login_url=LOGIN_URL)
@csrf_exempt
def proxy_to_kibana(request):
    try:

        return proxy_request(request, host=KIBANA_SERVER, url=request.get_full_path(), data=request.body, stream=True)
        # use stream=True because kibana returns gziped responses, and this prevents the requests module from
        # automatically unziping them
    except ConnectionError as e:
        logger.error(e)

        return HttpResponse("Error: Unable to connect to Kibana")
