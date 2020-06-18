from __future__ import unicode_literals

import logging
import re

from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)


class DjangoJSONEncoderWithSets(DjangoJSONEncoder):

    def default(self, o):
        if isinstance(o, set):
            return list(o)

        return super(DjangoJSONEncoderWithSets, self).default(o)


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


CAMEL_CASE_MAP = {}


def _to_camel_case(snake_case_str):
    """Convert snake_case string to CamelCase"""
    if not CAMEL_CASE_MAP.get(snake_case_str):
        converted = snake_case_str.replace('_', ' ').title().replace(' ', '')
        CAMEL_CASE_MAP[snake_case_str] = converted[0].lower() + converted[1:]
    return CAMEL_CASE_MAP[snake_case_str]


def _to_title_case(snake_case_str):
    """Convert snake_case string to Title Case"""

    components = snake_case_str.split('_')
    return " ".join(x.title() for x in components)


def _to_snake_case(camel_case_str):
    """Convert CamelCase string to snake_case (from https://gist.github.com/jaytaylor/3660565)"""

    return re.sub('([A-Z])', '_\\1', camel_case_str).lower().lstrip('_')
