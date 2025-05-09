import json
import mock

from anymail.exceptions import AnymailError
from django.contrib import auth
from django.contrib.auth.models import User, Group
from django.urls.base import reverse
from guardian.shortcuts import get_perms
from urllib.parse import quote_plus

from seqr.models import UserPolicy, Project, CAN_VIEW, CAN_EDIT
from seqr.views.apis.users_api import get_all_collaborator_options, set_password, \
    create_project_collaborator, update_project_collaborator, delete_project_collaborator, forgot_password, \
    get_project_collaborator_options, update_policies, update_user, get_all_user_group_options, \
    update_project_collaborator_group, delete_project_collaborator_group
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase


PROJECT_GUID = 'R0001_1kg'
NON_ANVIL_PROJECT_GUID = 'R0002_empty'
USERNAME = 'test_user_collaborator'
COLLABORATOR_FIELDS = {'hasEditPermissions', 'hasViewPermissions', 'displayName', 'username', 'email'}
ANALYST_USERNAME = 'test_user'

MAIN_COLLABORATOR_JSON = {
    'test_user_manager': {
        'displayName': 'Test Manager User', 'username': 'test_user_manager', 'email': 'test_user_manager@test.com',
    },
    'test_user_collaborator': {
        'displayName': 'Test Collaborator User', 'username': 'test_user_collaborator', 'email': 'test_user_collaborator@test.com',
    },
}

TOS_VERSION = 2.2
PRIVACY_VERSION = 1.1


class UsersAPITest(object):

    @mock.patch('seqr.views.utils.orm_to_json_utils.ANALYST_USER_GROUP', 'analysts')
    def test_get_project_collaborator_options(self):
        url = reverse(get_project_collaborator_options, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        if hasattr(self, 'mock_get_ws_acl'):
            self.mock_get_ws_acl.reset_mock()
            self.mock_get_ws_access_level.reset_mock()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        users = {
            ANALYST_USERNAME: {
                'displayName': 'Test User', 'username': 'test_user', 'email': 'test_user@broadinstitute.org',
            },
            'test_pm_user': {
                'displayName': 'Test PM User', 'username': 'test_pm_user', 'email': 'test_pm_user@test.com',
            },
        }
        users.update(self.COLLABORATOR_JSON)
        users.pop('analysts@firecloud.org', None)
        self.assertDictEqual(response_json, users)
        return url

    def test_get_all_collaborator_options(self):
        url = reverse(get_all_collaborator_options)
        self.check_require_login(url)

        response = self.client.get(url)
        self._test_logged_in_collaborator_options_response(response)

        self.login_collaborator()
        response = self.client.get(url)
        self._test_collaborator_collaborator_options_response(response)

    def _test_logged_in_collaborator_options_response(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(list(response.json().keys()), [])

    def _test_collaborator_collaborator_options_response(self, response):
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), set(self.COLLABORATOR_JSON.keys()))
        self.assertSetEqual(
            set(response_json['test_user_manager'].keys()), {'firstName', 'lastName', 'username', 'email'})

    def test_get_all_user_group_options(self):
        url = reverse(get_all_user_group_options)
        self.check_require_login(url)

        response = self.client.get(url)
        self._test_user_group_options_response(response)

    def _test_user_group_options_response(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'groups': ['analysts', 'project-managers']})

    @mock.patch('django.contrib.auth.models.send_mail')
    def test_create_project_collaborator(self, mock_send_mail):
        create_url = reverse(create_project_collaborator, args=[NON_ANVIL_PROJECT_GUID])
        self.check_manager_login(create_url)
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({}))
        self._test_create_project_collaborator(
            response, create_url=create_url, mock_send_mail=mock_send_mail)

    def _test_create_project_collaborator(self, response, create_url=None, mock_send_mail=None):
        # send invalid request
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Email is required')

        # create
        self.reset_logs()
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({
            'email': 'test@test.com', 'firstName': 'Test'}))
        self.assertEqual(response.status_code, 200)
        collaborators = response.json()['projectsByGuid'][NON_ANVIL_PROJECT_GUID]['collaborators']
        self.assertEqual(len(collaborators), 3)
        self.assertListEqual(
            [c['displayName'] for c in collaborators],
            ['Test Manager User', 'Test', 'Test Collaborator User'])
        new_collaborator = collaborators[1]
        self.assertSetEqual(set(new_collaborator.keys()), COLLABORATOR_FIELDS)
        self.assertEqual(new_collaborator['email'], 'test@test.com')
        self.assertEqual(new_collaborator['displayName'], 'Test')
        self.assertTrue(new_collaborator['hasViewPermissions'])
        self.assertFalse(new_collaborator['hasEditPermissions'])

        username = new_collaborator['username']
        user = User.objects.get(username=username)

        expected_email_content = """
    Hi there Test--

    Test Manager User has added you as a collaborator in seqr.

    Please click this link to set up your account:
    /login/set_password/{password_token}

    Thanks!
    """.format(password_token=user.password)
        mock_send_mail.assert_called_with(
            'Set up your seqr account',
            expected_email_content,
            None,
            ['test@test.com'],
            fail_silently=False,
        )
        mock_send_mail.reset_mock()

        self.assert_json_logs(self.manager_user, [('Created user test@test.com (local)', None)])
        self.reset_logs()

        # check user object added to project set
        self.assertEqual(
            Project.objects.get(guid=NON_ANVIL_PROJECT_GUID).can_view_group.user_set.filter(username=username).count(), 1)

        # calling create again just updates the existing user
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({
            'email': 'Test@test.com', 'firstName': 'Test', 'lastName': 'Name Update'}))
        self.assertEqual(response.status_code, 200)
        collaborators = response.json()['projectsByGuid'][NON_ANVIL_PROJECT_GUID]['collaborators']
        self.assertEqual(len(collaborators), 3)
        new_collab = next(collab for collab in collaborators if collab['email'] == 'test@test.com')
        self.assertEqual(new_collab['username'], username)
        self.assertEqual(new_collab['displayName'], 'Test Name Update')
        new_user_model = User.objects.get(username=new_collab['username'])
        self.assert_json_logs(user, [(f'update User {new_user_model.id}', {'dbUpdate': {
            'dbEntity': 'User', 'entityId': new_user_model.id, 'updateFields': ['last_name'], 'updateType': 'update'}})])

        # Test email failure
        mock_send_mail.side_effect = AnymailError('Connection err')
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({
            'email': 'Test_new@test.com'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Connection err')

    def test_update_project_collaborator(self):
        update_url = reverse(update_project_collaborator, args=[PROJECT_GUID, USERNAME])
        self.check_manager_login(update_url)

        response = self.client.post(update_url, content_type='application/json', data=json.dumps(
            {'hasEditPermissions': True}
        ))
        self._test_update_collaborator_response(response)

    def _test_update_collaborator_response(self, response):
        collaborators = response.json()['projectsByGuid'][PROJECT_GUID]['collaborators']
        self.assertEqual(len(collaborators), len(self.COLLABORATOR_JSON))
        edited_collab = next(collab for collab in collaborators if collab['username'] == USERNAME)
        self.assertNotEqual(edited_collab['displayName'], 'Edited Collaborator')
        self.assertTrue(edited_collab['hasViewPermissions'])
        self.assertEqual(edited_collab['hasEditPermissions'], True)

    def test_delete_project_collaborator(self):
        delete_url = reverse(delete_project_collaborator, args=[PROJECT_GUID, USERNAME])
        self.check_manager_login(delete_url)

        response = self.client.post(delete_url, content_type='application/json')
        self._test_delete_collaborator_response(response)

    def _test_delete_collaborator_response(self, response):
        self.assertEqual(response.status_code, 200)
        collaborators = response.json()['projectsByGuid'][PROJECT_GUID]['collaborators']
        self.assertEqual(len(collaborators), len(self.COLLABORATOR_JSON) - 1)

        # check that user still exists
        self.assertEqual(User.objects.filter(username=USERNAME).count(), 1)

    def test_update_project_collaborator_group(self):
        update_url = reverse(update_project_collaborator_group, args=[PROJECT_GUID, 'project-managers'])
        self.check_manager_login(update_url)

        response = self.client.post(update_url, content_type='application/json', data=json.dumps(
            {'hasEditPermissions': True}
        ))
        self._test_update_collaborator_group_response(response, update_url=update_url)

    def _test_update_collaborator_group_response(self, response, update_url=None):
        self.assertEqual(response.status_code, 200)
        groups = response.json()['projectsByGuid'][PROJECT_GUID]['collaboratorGroups']
        self.assertEqual(len(groups), 2)
        self.assertDictEqual(
            groups[1], {'name': 'project-managers', 'hasViewPermissions': True, 'hasEditPermissions': True})
        project = Project.objects.get(guid=PROJECT_GUID)
        self.assertSetEqual(set(get_perms(Group.objects.get(name='project-managers'), project)), {CAN_VIEW, CAN_EDIT})

        response = self.client.post(update_url, content_type='application/json', data=json.dumps(
            {'hasEditPermissions': False}
        ))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json()['projectsByGuid'][PROJECT_GUID]['collaboratorGroups'][1],
            {'name': 'project-managers', 'hasViewPermissions': True, 'hasEditPermissions': False},
        )
        self.assertSetEqual(set(get_perms(Group.objects.get(name='project-managers'), project)), {CAN_VIEW})

    def test_delete_project_collaborator_group(self):
        delete_url = reverse(delete_project_collaborator_group, args=[PROJECT_GUID, 'analysts'])
        self.check_manager_login(delete_url)

        response = self.client.post(delete_url, content_type='application/json')
        self._test_delete_collaborator_group_response(response)

    def _test_delete_collaborator_group_response(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()['projectsByGuid'][PROJECT_GUID]['collaboratorGroups'], [])

        # check that group still exists
        groups = Group.objects.filter(name='analysts')
        self.assertEqual(groups.count(), 1)
        self.assertListEqual(get_perms(groups.first(), Project.objects.get(guid=PROJECT_GUID)), [])

    def test_set_password(self):
        username = 'test_new_user'
        user = User.objects.create_user(username)
        auth_user = auth.get_user(self.client)
        self.assertNotEqual(user, auth_user)

        set_password_url = reverse(set_password, args=[username])
        self._test_set_password(set_password_url, user.password)

    def _test_set_password(self, url, *args, **kwargs):
        self._test_password_auth_disabled(url)

    def test_forgot_password(self):
        url = reverse(forgot_password)
        self._test_forgot_password(url)

    def _test_forgot_password(self, url, *args, **kwargs):
        self._test_password_auth_disabled(url)

    def _test_password_auth_disabled(self, url):
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

    @mock.patch('seqr.views.apis.users_api.SEQR_TOS_VERSION')
    @mock.patch('seqr.views.apis.users_api.SEQR_PRIVACY_VERSION')
    def test_update_policies(self, mock_privacy, mock_tos):
        mock_privacy.resolve_expression.return_value = PRIVACY_VERSION
        mock_tos.resolve_expression.return_value = TOS_VERSION
        self.assertEqual(UserPolicy.objects.filter(user=self.no_policy_user).count(), 0)

        url = reverse(update_policies)
        self.check_require_login_no_policies(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'User must accept current policies')

        response = self.client.post(url, content_type='application/json', data=json.dumps({'acceptedPolicies': True}))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'currentPolicies': True})

        new_policy = UserPolicy.objects.get(user=self.no_policy_user)
        self.assertEqual(new_policy.privacy_version, PRIVACY_VERSION)
        self.assertEqual(new_policy.tos_version, TOS_VERSION)

        # Test updating user with out of date policies
        mock_privacy.resolve_expression.return_value = PRIVACY_VERSION + 1
        mock_tos.resolve_expression.return_value = TOS_VERSION + 2

        response = self.client.post(url, content_type='application/json', data=json.dumps({'acceptedPolicies': True}))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'currentPolicies': True})

        existing_policy = UserPolicy.objects.get(user=self.no_policy_user)
        self.assertEqual(existing_policy.privacy_version, PRIVACY_VERSION + 1)
        self.assertEqual(existing_policy.tos_version, TOS_VERSION + 2)

    def test_update_user(self):
        url = reverse(update_user)
        self.check_require_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'email': 'Test@test.com', 'firstName': 'New', 'lastName': 'Username', 'isSuperuser': True}))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'firstName': 'New',
            'lastName': 'Username',
            'displayName': 'New Username',
        })

        user = User.objects.get(email='test_user_no_access@test.com')
        self.assertEqual(user.get_full_name(), 'New Username')
        self.assertFalse(user.is_superuser)


# Tests for AnVIL access disabled
class LocalUsersAPITest(AuthenticationTestCase, UsersAPITest):
    fixtures = ['users', '1kg_project']
    COLLABORATOR_JSON = MAIN_COLLABORATOR_JSON

    @mock.patch('django.contrib.auth.models.send_mail')
    def _test_forgot_password(self, url, mock_send_mail): # pylint: disable=arguments-differ
        # send invalid requests
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Email is required')

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'email': 'test_new_user@test.com'
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'No account found for this email')

        # Send valid request
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'email': 'test_user@broadinstitute.org'
        }))
        self.assertEqual(response.status_code, 200)

        expected_email_content = """
        Hi there Test User--

        Please click this link to reset your seqr password:
        /login/set_password/pbkdf2_sha256%2430000%24y85kZgvhQ539%24jrEC3L1IhCezUx3Itp%2B14w%2FT7U6u5XUxtpBZXKv8eh4%3D?reset=true
        """
        mock_send_mail.assert_called_with(
            'Reset your seqr password',
            expected_email_content,
            None,
            ['test_user@broadinstitute.org'],
            fail_silently=False,
        )

        # Test email failure
        mock_send_mail.side_effect = AnymailError('Connection err')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'email': 'test_user@broadinstitute.org'
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Connection err')

    def _test_set_password(self, set_password_url, password): # pylint: disable=arguments-differ
        response = self.client.post(set_password_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        response = self.client.post(set_password_url, content_type='application/json', data=json.dumps(
            {'userToken': 'invalid'}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        response = self.client.post(set_password_url, content_type='application/json', data=json.dumps(
            {'userToken': quote_plus(password)}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Password is required')

        response = self.client.post(set_password_url, content_type='application/json', data=json.dumps({
            'userToken': quote_plus(password), 'password': 'password123', 'firstName': 'Test', 'isSuperuser': True}))
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username='test_new_user')
        self.assertEqual(user.first_name, 'Test')
        self.assertFalse(user.password == password)
        self.assertFalse(user.is_superuser)

        auth_user = auth.get_user(self.client)
        self.assertEqual(user, auth_user)


class AnvilUsersAPITest(AnvilAuthenticationTestCase, UsersAPITest):
    fixtures = ['users', 'social_auth', '1kg_project']
    COLLABORATOR_JSON = {
        'test_user_pure_anvil@test.com': {
            'displayName': '', 'username': 'test_user_pure_anvil@test.com', 'email': 'test_user_pure_anvil@test.com',
        },
        'analysts@firecloud.org': {
            'displayName': '', 'username': 'analysts@firecloud.org', 'email': 'analysts@firecloud.org',
        },
    }
    COLLABORATOR_JSON.update(MAIN_COLLABORATOR_JSON)

    def _assert_403_response(self, response, **kwargs):
        self.assertEqual(response.status_code, 403)
        self.mock_list_workspaces.assert_not_called()
        self.assert_no_extra_anvil_calls()

    _test_logged_in_collaborator_options_response = _assert_403_response
    _test_collaborator_collaborator_options_response = _assert_403_response
    _test_user_group_options_response = _assert_403_response
    _test_create_project_collaborator = _assert_403_response
    _test_update_collaborator_response = _assert_403_response
    _test_delete_collaborator_response = _assert_403_response
    _test_update_collaborator_group_response = _assert_403_response
    _test_delete_collaborator_group_response = _assert_403_response

    def test_get_project_collaborator_options(self, *args, **kwargs):
        url = super(AnvilUsersAPITest, self).test_get_project_collaborator_options(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.assertEqual(self.mock_get_ws_acl.call_count, 1)
        self.mock_get_ws_acl.assert_called_with(
            self.collaborator_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.assertEqual(self.mock_get_ws_access_level.call_count, 1)
        self.mock_get_ws_access_level.assert_called_with(
            self.collaborator_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.mock_get_groups.assert_not_called()
        self.mock_get_group_members.assert_called_with(self.collaborator_user, 'Analysts', use_sa_credentials=True)

        self.mock_get_ws_acl.side_effect = lambda *args: {}
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'test_user_collaborator': MAIN_COLLABORATOR_JSON['test_user_collaborator']})

    def test_set_password(self):
        super(AnvilUsersAPITest, self).test_set_password()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()

    def test_forgot_password(self, *args, **kwargs):
        super(AnvilUsersAPITest, self).test_forgot_password(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()

    def test_update_policies(self, *args, **kwargs):
        super(AnvilUsersAPITest, self).test_update_policies(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_groups.assert_not_called()
        self.mock_get_group_members.assert_not_called()
