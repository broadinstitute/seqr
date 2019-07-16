import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from requests.exceptions import ConnectionError

from seqr.views.utils.proxy_request_utils import proxy_request
from settings import LOGIN_URL, KIBANA_SERVER

logger = logging.getLogger(__name__)



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
