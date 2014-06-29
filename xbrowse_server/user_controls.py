from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from xbrowse_server.base.models import Project


def add_new_collaborator(email, referrer):
    """
    Someone has added a new user to the system - create user and email them
    Args:
        referrer (User): person that is adding this user; email will reference them.
    """
    username = User.objects.make_random_password()
    user = User.objects.create_user(username, email=email)
    profile = user.profile
    profile.set_password_token = User.objects.make_random_password(length=30)
    profile.save()

    link = settings.BASE_URL + user.profile.get_set_password_link()
    email_content = render_to_string('emails/new_collaborator.txt', {'user': user, 'link': link, 'referrer': referrer})
    send_mail('Set up your xBrowse account', email_content, settings.FROM_EMAIL, [user.email,], fail_silently=False )

    return user


def get_projects_for_user(user):
    """

    """
    if user.is_staff:
        return Project.objects.all()
    else:
        return [p for p in Project.objects.all() if p.can_view(user)]


def get_fellow_collaborators(user):
    """
    All the users that collaborate on any project with user
    """
    pass