import json
import re
from datetime import datetime
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.middleware.csrf import rotate_token
from django.template import loader
from django.http import HttpResponse
from settings import (
    SEQR_VERSION,
    CSRF_COOKIE_NAME,
    DEBUG,
    LOGIN_URL,
    GA_TOKEN_ID,
    ANVIL_LOADING_DELAY_EMAIL_START_DATE,
    SOCIAL_AUTH_PROVIDER,
    VLM_CLIENT_ID,
)
from seqr.models import WarningMessage
from seqr.utils.search.utils import backend_specific_call
from seqr.views.utils.orm_to_json_utils import get_json_for_user, get_json_for_current_user
from seqr.views.utils.permissions_utils import login_active_required


@login_active_required(login_url=LOGIN_URL)
def main_app(request, *args, **kwargs):
    """Loads the react single page app."""
    return render_app_html(request)


def no_login_main_app(request, *args, **kwargs):
    """Loads the react single page app for non-logged in views."""
    render_kwargs = {'include_user': False}
    user_token = kwargs.get('user_token')
    if user_token:
        render_kwargs['additional_json'] = {'newUser': get_json_for_user(
            User.objects.get(password=user_token), fields=['id', 'first_name', 'last_name', 'username', 'email'],
        )}
    elif not request.user.is_anonymous:
        render_kwargs['include_user'] = True
    if not request.META.get(CSRF_COOKIE_NAME):
        rotate_token(request)
    return render_app_html(request, **render_kwargs)


def render_app_html(request, additional_json=None, include_user=True, status=200):
    html = loader.render_to_string('app.html')

    app_js_script = re.search('static/app-(.*)\.js', html)
    if app_js_script:
        ui_version = app_js_script.group(1)
    else:
        ui_version = 'local'
        html = html.replace('</head>', '<script defer="defer" src="/app.js"></script></head>')

    should_show_loading_delay = bool(ANVIL_LOADING_DELAY_EMAIL_START_DATE)
    if should_show_loading_delay:
        should_show_loading_delay = datetime.strptime(ANVIL_LOADING_DELAY_EMAIL_START_DATE, '%Y-%m-%d') < datetime.now()
    initial_json = {'meta':  {
        'version': '{}-{}'.format(SEQR_VERSION, ui_version),
        'hijakEnabled': DEBUG or False,
        'oauthLoginProvider': SOCIAL_AUTH_PROVIDER,
        'elasticsearchEnabled': backend_specific_call(True, False, False),
        'vlmEnabled': bool(VLM_CLIENT_ID),
        'warningMessages': [message.json() for message in WarningMessage.objects.all()],
        'anvilLoadingDelayDate': ANVIL_LOADING_DELAY_EMAIL_START_DATE if should_show_loading_delay else None,
    }}
    if include_user:
        initial_json['user'] = get_json_for_current_user(request.user)
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

    # initialize Google Analytics
    if GA_TOKEN_ID:
        html = html.replace(
            'window.gaTrackingId=null',
            'window.gaTrackingId="{}"'.format(GA_TOKEN_ID),
        )
        if include_user:
            html = html.replace(
                'window.userEmail=null',
                f'window.userEmail="{request.user.email}"',
            )

    return HttpResponse(html, content_type="text/html", status=status)
