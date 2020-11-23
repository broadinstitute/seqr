import json
import re
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.middleware.csrf import rotate_token
from django.template import loader
from django.http import HttpResponse
from settings import SEQR_VERSION, SEQR_PRIVACY_VERSION, SEQR_TOS_VERSION, CSRF_COOKIE_NAME, DEBUG
from seqr.views.utils.orm_to_json_utils import _get_json_for_user
from seqr.views.utils.terra_api_utils import anvil_enabled


@login_required
def main_app(request, *args, **kwargs):
    """Loads the react single page app."""
    return _render_app_html(request, {'user': _get_json_for_initial_user(request.user)})


def no_login_main_app(request, *args, **kwargs):
    """Loads the react single page app for non-logged in views."""
    initial_json = {}
    user_token = kwargs.get('user_token')
    if user_token:
        initial_json['newUser'] = _get_json_for_initial_user(User.objects.get(password=user_token))
    elif not request.user.is_anonymous():
        initial_json['user'] = _get_json_for_initial_user(request.user)
    if not request.META.get(CSRF_COOKIE_NAME):
        rotate_token(request)
    return _render_app_html(request, initial_json)


def _get_json_for_initial_user(user):
    user_json = _get_json_for_user(user)

    user_json['currentPolicies'] = False
    if hasattr(user, 'userpolicy'):
        current_privacy = user.userpolicy.privacy_version
        current_tos = user.userpolicy.tos_version
        user_json['currentPolicies'] = current_privacy == SEQR_PRIVACY_VERSION and current_tos == SEQR_TOS_VERSION

    return user_json

def _render_app_html(request, initial_json):
    html = loader.render_to_string('app.html')
    ui_version = re.search('static/app-(.*)\.js', html).group(1)
    initial_json['meta'] = {
        'version': '{}-{}'.format(SEQR_VERSION, ui_version),
        'hijakEnabled': DEBUG or False,
        'googleLoginEnabled': anvil_enabled(),
    }

    html = html.replace(
        "window.initialJSON=null",
        "window.initialJSON=" + json.dumps(initial_json, default=DjangoJSONEncoder().default)
    )

    if request.get_host() == 'localhost:3000':
        html = re.sub(r'static/app(-.*)js', 'app.js', html)
        html = re.sub(r'<link\s+href="/static/app.*css"[^>]*>', '', html)

    return HttpResponse(html, content_type="text/html")