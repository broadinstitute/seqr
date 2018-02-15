from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings

from settings import LOGIN_URL
from xbrowse_server.base.utils import get_projects_for_user


@staff_member_required(login_url=LOGIN_URL)
def last_1000_views(request):
    views = settings.LOGGING_DB.pageviews.find({'page': {'$ne': 'home'}}).sort([('date', -1)])[:5000]
    views = [v for v in views if v.get('ip_addr') != "127.0.0.1"]
    return render(request, 'staff/last_1000_views.html', {
        'views': views, 
    })


@staff_member_required(login_url=LOGIN_URL)
def userinfo(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'staff/userinfo.html', {
        'user': user,
        'profile': user.profile,
        'projects': get_projects_for_user(user),
    })
