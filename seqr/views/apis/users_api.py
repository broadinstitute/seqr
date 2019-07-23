import itertools
import json
import urllib
from anymail.exceptions import AnymailError
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user
from seqr.views.utils.permissions_utils import get_projects_user_can_view, get_project_and_check_permissions, CAN_EDIT
from seqr.model_utils import create_xbrowse_project_collaborator, delete_xbrowse_project_collaborator


class CreateUserException(Exception):
    def __init__(self, error, status_code=400, existing_user=None):
        Exception.__init__(self, error)
        self.status_code = status_code
        self.existing_user = existing_user


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def get_all_collaborators(request):
    if request.user.is_staff:
        collaborators = {user.username: _get_json_for_user(user) for user in User.objects.exclude(email='')}
    else:
        collaborators = {}
        for project in get_projects_user_can_view(request.user):
            collaborators.update(_get_project_collaborators(project, include_permissions=False))

    return create_json_response(collaborators)


@csrf_exempt
def forgot_password(request):
    request_json = json.loads(request.body)
    if not request_json.get('email'):
        return create_json_response({}, status=400, reason='Email is required')

    users = User.objects.filter(email__iexact=request_json['email'])
    if users.count() != 1:
        return create_json_response({}, status=400, reason='No account found for this email')
    user = users.first()

    email_content = """
        Hi there {full_name}--

        Please click this link to reset your seqr password:
        {base_url}users/set_password/{password_token}?reset=true
        """.format(
        full_name=user.get_full_name(),
        base_url=settings.BASE_URL,
        password_token=urllib.quote_plus(user.password),
    )

    try:
        user.email_user('Reset your seqr password', email_content, fail_silently=False)
    except AnymailError as e:
        return create_json_response({}, status=getattr(e, 'status_code', None) or 400, reason=str(e))

    return create_json_response({'success': True})


@csrf_exempt
def set_password(request, username):
    user = User.objects.get(username=username)

    request_json = json.loads(request.body)
    if not request_json.get('password'):
        return create_json_response({}, status=400, reason='Password is required')

    user.set_password(request_json['password'])
    user.first_name = request_json.get('firstName') or ''
    user.last_name = request_json.get('lastName') or ''
    user.save()

    u = authenticate(username=username, password=request_json['password'])
    login(request, u)

    return create_json_response({'success': True})


@staff_member_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_staff_user(request):
    try:
        _create_user(request, is_staff=True)
    except CreateUserException as e:
        return create_json_response({'error': e.message}, status=e.status_code, reason=e.message)

    return create_json_response({'success': True})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_project_collaborator(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)

    try:
        user = _create_user(request)
    except CreateUserException as e:
        if e.existing_user:
            return _update_existing_user(e.existing_user, project, json.loads(request.body))
        else:
            return create_json_response({'error': e.message}, status=e.status_code, reason=e.message)

    project.can_view_group.user_set.add(user)
    create_xbrowse_project_collaborator(project, user)

    return create_json_response({
        'projectsByGuid': {project_guid: {'collaborators': get_json_for_project_collaborator_list(project)}}
    })


def _create_user(request, is_staff=False):
    request_json = json.loads(request.body)
    if not request_json.get('email'):
        raise CreateUserException('Email is required')

    existing_user = User.objects.filter(email__iexact=request_json['email']).first()
    if existing_user:
        raise CreateUserException('This user already exists', existing_user=existing_user)

    username = User.objects.make_random_password()
    user = User.objects.create_user(
        username,
        email=request_json['email'],
        first_name=request_json.get('firstName') or '',
        last_name=request_json.get('lastName') or '',
        is_staff=is_staff,
    )

    try:
        send_welcome_email(user, request.user)
    except AnymailError as e:
        raise CreateUserException(str(e), status_code=getattr(e, 'status_code', None) or 400)

    return user


def send_welcome_email(user, referrer):
    email_content = """
    Hi there {full_name}--

    {referrer} has added you as a collaborator in seqr.

    Please click this link to set up your account:
    {base_url}users/set_password/{password_token}

    Thanks!
    """.format(
        full_name=user.get_full_name(),
        referrer=referrer.get_full_name() or referrer.email,
        base_url=settings.BASE_URL,
        password_token=user.password,
    )
    user.email_user('Set up your seqr account', email_content, fail_silently=False)


def _update_existing_user(user, project, request_json):
    user.first_name = request_json.get('firstName') or ''
    user.last_name = request_json.get('lastName') or ''
    user.save()

    project.can_view_group.user_set.add(user)
    if request_json.get('hasEditPermissions'):
        project.can_edit_group.user_set.add(user)
    else:
        project.can_edit_group.user_set.remove(user)

    create_xbrowse_project_collaborator(
        project, user, collaborator_type='manager' if request_json.get('hasEditPermissions') else 'collaborator')

    return create_json_response({
        'projectsByGuid': {project.guid: {'collaborators': get_json_for_project_collaborator_list(project)}}
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_project_collaborator(request, project_guid, username):
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)
    user = User.objects.get(username=username)

    request_json = json.loads(request.body)
    return _update_existing_user(user, project, request_json)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_project_collaborator(request, project_guid, username):
    project = get_project_and_check_permissions(project_guid, request.user, permission_level=CAN_EDIT)
    user = User.objects.get(username=username)

    project.can_view_group.user_set.remove(user)
    project.can_edit_group.user_set.remove(user)

    delete_xbrowse_project_collaborator(project, user)

    return create_json_response({
        'projectsByGuid': {project_guid: {'collaborators': get_json_for_project_collaborator_list(project)}}
    })


def get_json_for_project_collaborator_list(project):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborator_list = _get_project_collaborators(project).values()

    return sorted(collaborator_list, key=lambda collaborator: (collaborator['lastName'], collaborator['displayName']))


def _get_project_collaborators(project, include_permissions=True):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborators = {}

    for collaborator in project.can_view_group.user_set.all():
        collaborators[collaborator.username] = _get_collaborator_json(
            collaborator, include_permissions, can_edit=False
        )

    for collaborator in itertools.chain(project.owners_group.user_set.all(), project.can_edit_group.user_set.all()):
        collaborators[collaborator.username] = _get_collaborator_json(
            collaborator, include_permissions, can_edit=True
        )

    return collaborators


def _get_collaborator_json(collaborator, include_permissions, can_edit):
    collaborator_json = _get_json_for_user(collaborator)
    if include_permissions:
        collaborator_json.update({
            'hasViewPermissions': True,
            'hasEditPermissions': can_edit,
        })
    return collaborator_json

