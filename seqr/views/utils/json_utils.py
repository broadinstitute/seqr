import json
import logging

from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.template import loader
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class DjangoJSONEncoderWithSets(DjangoJSONEncoder):

    def default(self, o):
        if isinstance(o, set):
            return list(o)

        return super(DjangoJSONEncoderWithSets, self).default(o)



def render_with_initial_json(html_page, initial_json):
    """Uses django template rendering utilities to read in the given html file, and embed the
    given object as json within the page. This way when the browser sends an initial request
    for the page, it comes back with the json bundle already embedded in it.

    Args:
        html_page (string): path of html template
        initial_json (object): the object to be serialized to json
    Returns:
        HttpResponse: django HttpRepsonse object to send back to the client
    """

    initial_json_str = json.dumps(
        initial_json,
        sort_keys=True,
        indent=4,
        default=DjangoJSONEncoderWithSets().default
    )

    html = loader.render_to_string(html_page)

    html = html.replace(
        "window.initialJSON=null",
        "window.initialJSON="+initial_json_str
    )
    return HttpResponse(html, content_type="text/html")


def create_json_response(obj, **kwargs):
    """Encodes the give object into json and create a django JsonResponse object with it.

    Args:
        obj (object): json response object
        **kwargs: any addition args to pass to the JsonResponse constructor
    Returns:
        JsonResponse
    """

    dumps_params = {
        'sort_keys': True,
        'indent': 4,
        'default': DjangoJSONEncoderWithSets().default
    }

    return JsonResponse(
        obj, json_dumps_params=dumps_params, encoder=DjangoJSONEncoderWithSets, **kwargs)


def _to_camel_case(snake_case_str):
    """Convert snake_case string to CamelCase"""

    components = snake_case_str.split('_')
    return components[0] + "".join(x.title() for x in components[1:])


def _to_title_case(snake_case_str):
    """Convert snake_case string to Title Case"""

    components = snake_case_str.split('_')
    return " ".join(x.title() for x in components)
