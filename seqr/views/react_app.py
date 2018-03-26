import json
import re
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.template import loader
from django.http import HttpResponse

from seqr.views.utils.orm_to_json_utils import _get_json_for_user


@login_required
def main_app(request, *args, **kwargs):
    """Loads the react single page app."""

    html = loader.render_to_string('app.html')

    html = html.replace(
        "window.initialJSON=null",
        "window.initialJSON=" + json.dumps(
            {'user': _get_json_for_user(request.user)},
            default=DjangoJSONEncoder().default
        )
    )

    if request.get_host() == 'localhost:3000':
        html = re.sub(r'static/app(-.*)js', 'app.js', html)

    return HttpResponse(html, content_type="text/html")