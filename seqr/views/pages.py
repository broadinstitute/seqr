from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import json
import seqr.views.api
from django.core.serializers.json import DateTimeAwareJSONEncoder

"""
Reasons to use server-side django templates instead of putting all logic in the client:
 - easier to do login checks / redirects
 - can package data in the initial request
"""

@login_required
def dashboard(request):
    initial_json = {}
    initial_json.update( json.loads(seqr.views.api.projects_and_stats(request).content) )
    initial_json.update( json.loads(seqr.views.api.user(request).content) )

    initial_json_str = json.dumps(initial_json, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    return render(request, 'react_template.html', context={
        'webpack_bundle': 'dashboard',
        'page_title': 'Dashboard',
        'initial_json': initial_json_str,
    })


@login_required
def search(request):
    #initial_json = json.loads(seqr.views.api.case_review_page_data(request).content)
    #initial_json_str = json.dumps(initial_json, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    return render(request, 'react_template.html', context={
        'webpack_bundle': 'search',
        'page_title': 'seqr: Search',
        'initial_json': seqr.views.api.case_review_data(request).content,
    })



@login_required
def case_review(request, project_guid):
    initial_json = json.loads(seqr.views.api.case_review_data(request, project_guid).content)
    initial_json_str = json.dumps(initial_json, sort_keys=True, indent=4, default=DateTimeAwareJSONEncoder().default)

    return render(request, 'react_template.html', context={
        'webpack_bundle': 'case_review',
        'page_title': 'seqr: Case Review',
        'initial_json': initial_json_str,
    })

