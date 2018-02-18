import json
import logging

from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.mail import send_mail
from django.template import RequestContext
from django.template.loader import render_to_string
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required

from settings import LOGIN_URL
from xbrowse_server.base.forms import LoginForm, SetUpAccountForm
from xbrowse_server.base.models import UserProfile
from xbrowse_server.base.utils import get_projects_for_user
from xbrowse_server.decorators import log_request


def landing_page(request):
    return render(request, 'landing_page.html', {})


@csrf_exempt
def errorlog(request):

    logger = logging.getLogger(__name__)
    logger.error('xbrowse JS error', extra={'request': request})
    return HttpResponse(json.dumps({'success': True}))


@log_request('home')
def home(request):

    if request.user.is_anonymous():
        return landing_page(request)

    projects = get_projects_for_user(request.user)

    return render(request, 'home.html', {
        'user': request.user,
        'projects': projects, 
    })


@login_required
def about(request): 
    return render(request, 'about.html')


@log_request('login')
def login_view(request):

    logout(request)
    next = request.GET.get('next')

    if request.method == 'POST': 

        form = LoginForm(request.POST)
        if form.is_valid(): 
            user = form.user
            login(request, user)
            if next and '.wsgi' not in next:
                return redirect(next)
            else: 
                return redirect('home')

    else: 
        form = LoginForm()

    return render(request, 'login.html', {
        'form': form, 
        'next': next, 
    })


def logout_view(request):

    logout(request)
    return redirect('home')


@log_request('set_password')
def set_password(request):

    error = None

    token = request.GET.get('token')
    if not token or len(token) < 1: 
        return HttpResponse('Invalid')

    profile = get_object_or_404(UserProfile, set_password_token=token)

    if request.method == 'POST': 
        form = SetUpAccountForm(request.POST)
        if form.is_valid(): 
            user = profile.user
            user.set_password(form.cleaned_data['password1'])
            user.save()

            profile.set_password_token = ''
            profile.display_name = form.cleaned_data['name']
            profile.save()
            
            u = authenticate(username=profile.user.username, password=form.cleaned_data['password1'])
            login(request, u)
            return redirect('home')

    else: 
        form = SetUpAccountForm()

    return render(request, 'set_password.html', {
        'form': form, 
        'error': error, 
    })


def forgot_password(request):

    error = None

    if request.method == 'POST': 
        email = request.POST.get('email').lower()
        if email is None or email == "": 
            error = "Please enter an email."
        elif not User.objects.filter(email=email).exists(): 
            error = "This email address is not valid."
        else: 
            user = User.objects.get(email=email)
            profile = user.profile
            profile.set_password_token = User.objects.make_random_password(length=30)
            profile.save()
            email_content = render_to_string(
                'emails/reset_password.txt',
                {'user': user, 'BASE_URL': settings.BASE_URL },
            )
            send_mail('Reset your xBrowse password', email_content, settings.FROM_EMAIL, [email,], fail_silently=False )
            return redirect('forgot_password_sent')

    return render(request, 'forgot_password.html', {
        'error': error, 
    })


def forgot_password_sent(request):

    return render(request, 'forgot_password_sent.html', {
    })


def style_css(request): 
    return render(request, 'css/style.css', {

    }, content_type="text/css")


@log_request('user_summary')
@staff_member_required(login_url=LOGIN_URL)
def user_summary(request, username):
    user = User.objects.get(username=username)
    return render(request, 'user_summary.html', {
        'user': user,
        'projects': get_projects_for_user(user),
    })
