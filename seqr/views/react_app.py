import json
import re
import urllib
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.template import loader
from django.http import HttpResponse

from seqr.views.utils.orm_to_json_utils import _get_json_for_user


@login_required
def main_app(request, *args, **kwargs):
    """Loads the react single page app."""
    return _render_app_html(request, {'user': _get_json_for_user(request.user)})


def no_login_main_app(request, *args, **kwargs):
    """Loads the react single page app for non-logged in views."""
    initial_json = {}
    user_token = kwargs.get('user_token')
    if user_token:
        initial_json['newUser'] = _get_json_for_user(User.objects.get(password=urllib.unquote_plus(user_token)))
    elif not request.user.is_anonymous():
        initial_json['user'] = _get_json_for_user(request.user)
    return _render_app_html(request, initial_json)


def _render_app_html(request, initial_json):
    html = loader.render_to_string('app.html')

    html = html.replace(
        "window.initialJSON=null",
        "window.initialJSON=" + json.dumps(initial_json, default=DjangoJSONEncoder().default)
    )

    if request.get_host() == 'localhost:3000':
        html = re.sub(r'static/app(-.*)js', 'app.js', html)
        html = re.sub(r'<link\s+href="/static/app.*css"[^>]*>', '', html)

    return HttpResponse(html, content_type="text/html")