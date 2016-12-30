import json
import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.template import loader
from django.http import HttpResponse

import seqr.views.api

logger = logging.getLogger(__name__)


def render(html_page, initial_json):
    initial_json_str = json.dumps(initial_json, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    html = loader.render_to_string(html_page)
    html = html.replace("window.intialJSON = null", "window.intialJSON = " + initial_json_str)
    return HttpResponse(html)

@login_required
def dashboard(request):
    initial_json = {}
    initial_json.update( json.loads(seqr.views.api.projects_and_stats(request).content) )
    initial_json.update( json.loads(seqr.views.api.user(request).content) )

    return render('dashboard.html', initial_json)

@login_required
def case_review(request, project_guid):
    initial_json = json.loads(seqr.views.api.case_review_data(request, project_guid).content)
    return render('case_review.html', initial_json)


@login_required
def search(request):
    #initial_json = json.loads(seqr.views.api.case_review_page_data(request).content)
    #initial_json_str = json.dumps(initial_json, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    return render(request, 'react_template.html', context={
        'initial_json': seqr.views.api.case_review_data(request).content,
    })

