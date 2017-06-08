import json
import hashlib

from django.http import HttpResponse
from django.conf import settings


def JSONResponse(content):
    return HttpResponse(json.dumps(content), content_type="application/json")


def form_error_string(form):
    """
    Form error as a single string
    Display first error we find - user will only see one error
    """
    for field in form:
        if field.errors:
            return "Error with '%s': %s" % (field.name, field.errors[0])
    n = form.non_field_errors()
    if n:
        return n[0]
    return ""


def get_json_hash(arbitrary_json):
    hasher = hashlib.md5()
    hasher.update(str(arbitrary_json))
    return hasher.hexdigest()[:16]


def get_cached_results(key):
    key_str = get_json_hash(key)
    doc = settings.UTILS_DB.generic_cache.find_one({'key': key_str})
    if doc:
        return doc['results']
    return None


def save_results_cache(key, arbitrary_json):
    key_str = get_json_hash(key)
    settings.UTILS_DB.generic_cache.update({'key': key_str}, {'$set': {'results': arbitrary_json}}, upsert=True)
