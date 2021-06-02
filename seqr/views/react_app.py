import json
import re
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.middleware.csrf import rotate_token
from django.template import loader
from django.http import HttpResponse
from settings import SEQR_VERSION, CSRF_COOKIE_NAME, DEBUG
from seqr.views.utils.orm_to_json_utils import _get_json_for_user
from seqr.views.utils.permissions_utils import login_active_required
from seqr.views.utils.terra_api_utils import google_auth_enabled


@login_active_required(login_url='/login')
def main_app(request, *args, **kwargs):
    """Loads the react single page app."""
    return render_app_html(request)


def no_login_main_app(request, *args, **kwargs):
    """Loads the react single page app for non-logged in views."""
    render_kwargs = {'include_user': False}
    user_token = kwargs.get('user_token')
    if user_token:
        render_kwargs['additional_json'] = {'newUser': _get_json_for_user(User.objects.get(password=user_token))}
    elif not request.user.is_anonymous:
        render_kwargs['include_user'] = True
    if not request.META.get(CSRF_COOKIE_NAME):
        rotate_token(request)
    return render_app_html(request, **render_kwargs)


def render_app_html(request, additional_json=None, include_user=True, status=200):
    html = loader.render_to_string('app.html')
    ui_version = re.search('static/app-(.*)\.js', html).group(1)
    initial_json = {'meta':  {
        'version': '{}-{}'.format(SEQR_VERSION, ui_version),
        'hijakEnabled': DEBUG or False,
        'googleLoginEnabled': google_auth_enabled(),
    }}
    if include_user:
        initial_json['user'] = _get_json_for_user(request.user)
    if additional_json:
        initial_json.update(additional_json)

    html = html.replace(
        "window.initialJSON=null",
        "window.initialJSON=" + json.dumps(initial_json, default=DjangoJSONEncoder().default)
    )
    #  window.__webpack_nonce__ is used by styled-components and the webpack dev style-loader
    html = html.replace(
        'window.__webpack_nonce__=null',
        'window.__webpack_nonce__="{}"'.format(request.csp_nonce),
    )
    html = html.replace(
        '<script type="text/javascript">',
        '<script type="text/javascript" nonce="{}">'.format(request.csp_nonce)
    )

    if request.get_host() == 'localhost:3000':
        html = re.sub(r'static/app(-.*)js', 'app.js', html)
        html = re.sub(r'<link\s+href="/static/app.*css"[^>]*>', '', html)

    return HttpResponse(html, content_type="text/html", status=status)
