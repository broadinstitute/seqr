from requests.utils import quote

import json
import logging
from anymail.exceptions import AnymailError
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from seqr.models import UserPolicy
from seqr.utils.communication_utils import send_welcome_email
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user, get_json_for_project_collaborator_list
from seqr.views.utils.permissions_utils import get_projects_user_can_view, get_project_and_check_permissions
from settings import API_LOGIN_REQUIRED_URL, BASE_URL, SEQR_TOS_VERSION, SEQR_PRIVACY_VERSION

logger = logging.getLogger(__name__)

USER_OPTION_FIELDS = {'display_name', 'first_name', 'last_name', 'username', 'email', 'is_analyst'}


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def get_all_collaborator_options(request):
    collaborators = set()
    for project in get_projects_user_can_view(request.user):
        collaborators.update(project.get_collaborators())

    return create_json_response({
        user.username: _get_json_for_user(user, fields=USER_OPTION_FIELDS) for user in collaborators
    })

def _get_all_analysts():
    return User.objects.filter(is_staff=True, is_active=True) # TODO

@login_required(login_url=API_LOGIN_REQUIRED_URL)
def get_all_analyst_options(request):
    analysts = {
        user.username: _get_json_for_user(user, fields=USER_OPTION_FIELDS) for user in _get_all_analysts()
    }

    return create_json_response(analysts)


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
        base_url=BASE_URL,
        password_token=quote(user.password, safe=''),
    )

    try:
        user.email_user('Reset your seqr password', email_content, fail_silently=False)
    except AnymailError as e:
        return create_json_response({}, status=getattr(e, 'status_code', None) or 400, reason=str(e))

    return create_json_response({'success': True})


def set_password(request, username):
    user = User.objects.get(username=username)

    request_json = json.loads(request.body)
    if not request_json.get('password'):
        return create_json_response({}, status=400, reason='Password is required')

    user.set_password(request_json['password'])
    update_model_from_json(user, _get_user_json(request_json), user=user, updated_fields={'password'})
    logger.info('Set password for user {}'.format(user.email), extra={'user': user})

    u = authenticate(username=username, password=request_json['password'])
    login(request, u)

    return create_json_response({'success': True})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_policies(request):
    request_json = json.loads(request.body)
    if not request_json.get('acceptedPolicies'):
        message = 'User must accept current policies'
        return create_json_response({'error': message}, status=400, reason=message)

    get_or_create_model_from_json(
        UserPolicy, {'user': request.user}, update_json={
            'privacy_version': SEQR_PRIVACY_VERSION,
            'tos_version': SEQR_TOS_VERSION,
        }, user=request.user)

    return create_json_response({'currentPolicies': True})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def create_project_collaborator(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)

    request_json = json.loads(request.body)
    if not request_json.get('email'):
        return create_json_response({'error': 'Email is required'}, status=400)

    existing_user = User.objects.filter(email__iexact=request_json['email']).first()
    if existing_user:
        return _update_existing_user(existing_user, project, request_json)

    username = User.objects.make_random_password()
    user = User.objects.create_user(
        username,
        email=request_json['email'],
        first_name=request_json.get('firstName') or '',
        last_name=request_json.get('lastName') or '',
    )
    logger.info('Created user {} (local)'.format(request_json['email']), extra={'user': request.user})

    try:
        send_welcome_email(user, request.user)
    except AnymailError as e:
        return create_json_response({'error': str(e)}, status=getattr(e, 'status_code', None) or 400, reason=str(e))

    project.can_view_group.user_set.add(user)

    return create_json_response({
        'projectsByGuid': {project_guid: {'collaborators': get_json_for_project_collaborator_list(request.user, project)}}
    })


def _get_user_json(request_json):
    return {k: request_json.get(k) or '' for k in ['firstName', 'lastName']}


def _update_existing_user(user, project, request_json):
    update_model_from_json(user, _get_user_json(request_json), user=user)

    project.can_view_group.user_set.add(user)
    if request_json.get('hasEditPermissions'):
        project.can_edit_group.user_set.add(user)
    else:
        project.can_edit_group.user_set.remove(user)

    return create_json_response({
        'projectsByGuid': {project.guid: {'collaborators': get_json_for_project_collaborator_list(user, project)}}
    })


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def update_project_collaborator(request, project_guid, username):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    user = User.objects.get(username=username)

    request_json = json.loads(request.body)
    return _update_existing_user(user, project, request_json)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def delete_project_collaborator(request, project_guid, username):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    user = User.objects.get(username=username)

    project.can_view_group.user_set.remove(user)
    project.can_edit_group.user_set.remove(user)

    return create_json_response({
        'projectsByGuid': {project_guid: {'collaborators': get_json_for_project_collaborator_list(request.user, project)}}
    })
