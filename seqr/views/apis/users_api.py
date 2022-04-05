from requests.utils import quote

import json
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from urllib.parse import unquote

from seqr.models import UserPolicy
from seqr.utils.communication_utils import send_welcome_email
from seqr.utils.logging_utils import SeqrLogger
from seqr.views.utils.json_to_orm_utils import update_model_from_json, get_or_create_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import _get_json_for_user, get_json_for_project_collaborator_list, \
    get_project_collaborators_by_username
from seqr.views.utils.permissions_utils import get_local_access_projects, get_project_and_check_permissions, \
    login_and_policies_required, login_active_required
from seqr.views.utils.terra_api_utils import google_auth_enabled
from settings import BASE_URL, SEQR_TOS_VERSION, SEQR_PRIVACY_VERSION

logger = SeqrLogger(__name__)

USER_OPTION_FIELDS = {'display_name', 'first_name', 'last_name', 'username', 'email', 'is_analyst'}


@login_and_policies_required
def get_all_collaborator_options(request):
    collaborators = set()
    for project in get_local_access_projects(request.user):
        collaborators.update(project.get_collaborators())

    return create_json_response({
        user.username: _get_json_for_user(user, fields=USER_OPTION_FIELDS) for user in collaborators
    })


@login_and_policies_required
def get_project_collaborator_options(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)
    users = get_project_collaborators_by_username(
        request.user, project, include_permissions=False, include_analysts=True, fields=USER_OPTION_FIELDS,
    )
    return create_json_response(users)


def forgot_password(request):
    if google_auth_enabled():
        raise PermissionDenied('Username/ password authentication is disabled')

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
        {base_url}login/set_password/{password_token}?reset=true
        """.format(
        full_name=user.get_full_name(),
        base_url=BASE_URL,
        password_token=quote(user.password, safe=''),
    )

    user.email_user('Reset your seqr password', email_content, fail_silently=False)

    return create_json_response({'success': True})


def set_password(request, username):
    if google_auth_enabled():
        raise PermissionDenied('Username/ password authentication is disabled')
    user = User.objects.get(username=username)

    request_json = json.loads(request.body)
    user_token = unquote(request_json.get('userToken', ''))
    if not user_token == user.password:
        raise PermissionDenied('Not authorized to update password')

    if not request_json.get('password'):
        return create_json_response({}, status=400, reason='Password is required')

    user.set_password(request_json['password'])
    _update_user_from_json(user, request_json, updated_fields={'password'})
    logger.info('Set password for user {}'.format(user.email), user)

    u = authenticate(username=username, password=request_json['password'])
    login(request, u)

    return create_json_response({'success': True})


@login_and_policies_required
def update_user(request):
    request_json = json.loads(request.body)
    _update_user_from_json(request.user, request_json)

    return create_json_response(_get_json_for_user(request.user))


@login_active_required
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


@login_and_policies_required
def create_project_collaborator(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    if project.workspace_name:
        raise PermissionDenied(
            'Adding collaborators directly in seqr is disabled. Users can be managed from the associated AnVIL workspace')

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
    logger.info('Created user {} (local)'.format(request_json['email']), request.user)

    send_welcome_email(user, request.user)

    project.can_view_group.user_set.add(user)

    return create_json_response({
        'projectsByGuid': {project_guid: {'collaborators': get_json_for_project_collaborator_list(request.user, project)}}
    })


def _update_user_from_json(user, request_json, **kwargs):
    user_json = {k: request_json.get(k) or '' for k in ['firstName', 'lastName']}
    update_model_from_json(user, user_json, user=user, **kwargs)


def _update_existing_user(user, project, request_json):
    project.can_view_group.user_set.add(user)
    if request_json.get('hasEditPermissions'):
        project.can_edit_group.user_set.add(user)
    else:
        project.can_edit_group.user_set.remove(user)

    return create_json_response({
        'projectsByGuid': {project.guid: {'collaborators': get_json_for_project_collaborator_list(user, project)}}
    })


@login_and_policies_required
def update_project_collaborator(request, project_guid, username):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    user = User.objects.get(username=username)

    request_json = json.loads(request.body)
    return _update_existing_user(user, project, request_json)


@login_and_policies_required
def delete_project_collaborator(request, project_guid, username):
    project = get_project_and_check_permissions(project_guid, request.user, can_edit=True)
    user = User.objects.get(username=username)

    project.can_view_group.user_set.remove(user)
    project.can_edit_group.user_set.remove(user)

    return create_json_response({
        'projectsByGuid': {project_guid: {'collaborators': get_json_for_project_collaborator_list(request.user, project)}}
    })
