from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from xbrowse_server.base.utils import get_projects_for_user


@login_required
@staff_member_required
def last_1000_views(request):
    views = settings.LOGGING_DB.pageviews.find({'page': {'$ne': 'home'}}).sort([('date', -1)])[:5000]
    views = [v for v in views if ('username' not in v or 'weisburd' not in v['username'])]
    return render(request, 'staff/last_1000_views.html', {
        'views': views, 
    })


@login_required
@staff_member_required
def userinfo(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'staff/userinfo.html', {
        'user': user,
        'profile': user.profile,
        'projects': get_projects_for_user(user),
    })
