import json
import logging

from django.http import JsonResponse
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.template import loader
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def render_with_initial_json(html_page, initial_json):
    initial_json_str = json.dumps(
        initial_json,
        sort_keys=True,
        indent=4,
        default=DateTimeAwareJSONEncoder().default
    )

    html = loader.render_to_string(html_page)

    html = html.replace(
        "window.initialJSON=null",
        "window.initialJSON="+initial_json_str
    )
    return HttpResponse(html)


def create_json_response(obj, **kwargs):
    dumps_params = {
        'sort_keys': True,
        'indent': 4,
        'default': DateTimeAwareJSONEncoder().default
    }

    return JsonResponse(obj, json_dumps_params=dumps_params, encoder=DateTimeAwareJSONEncoder, **kwargs)


def get_user_info(user):
    json_obj = {
        key: value for key, value in user._wrapped.__dict__.items()
        if not key.startswith("_") and key != "password"
    }

    return json_obj




"""
@login_required
def projects(request):
    "Returns information on all projects this user has access to"

    # look up all projects the user has permissions to view
    if request.user.is_staff:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(can_view_group__user=request.user)

    return _create_json_response({"projects": [p.json() for p in projects]})


@login_required
def families(request, project_guid):
    # get all families in a particular project


@login_required
def individuals(request):

"""
