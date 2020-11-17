import json
import mock

from anymail.exceptions import AnymailError
from django.contrib import auth
from django.contrib.auth.models import User
from django.urls.base import reverse

from seqr.models import UserPolicy
from seqr.views.apis.users_api import get_all_collaborators, set_password, get_all_staff, update_policies, \
    create_project_collaborator, update_project_collaborator, delete_project_collaborator, forgot_password
from seqr.views.utils.test_utils import AuthenticationTestCase, USER_FIELDS
from settings import SEQR_TOS_VERSION, SEQR_PRIVACY_VERSION


PROJECT_GUID = 'R0001_1kg'


class UsersAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    def test_get_all_staff(self):
        get_all_staff_url = reverse(get_all_staff)
        self.check_require_login(get_all_staff_url)
        response = self.client.get(get_all_staff_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        all_staff_usernames = list(response_json.keys())
        first_staff_user = response_json[all_staff_usernames[0]]

        self.assertSetEqual(set(first_staff_user), USER_FIELDS)
        self.assertTrue(first_staff_user['isStaff'])

    def test_get_all_collaborators(self):
        url = reverse(get_all_collaborators)
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(list(response.json().keys()), [])

        self.login_collaborator()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json().keys()), {'test_user_manager', 'test_user_non_staff'})

        self.login_staff_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json().keys()), {
            'test_user_manager', 'test_user_non_staff', 'test_user_no_access', 'test_user'})



    @mock.patch('django.contrib.auth.models.send_mail')
    def test_create_update_and_delete_project_collaborator(self, mock_send_mail):
        create_url = reverse(create_project_collaborator, args=[PROJECT_GUID])
        self.check_manager_login(create_url)

        # send invalid request
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Email is required')

        # create
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({
            'email': 'test@test.com'}))
        self.assertEqual(response.status_code, 200)
        collaborators = response.json()['projectsByGuid'][PROJECT_GUID]['collaborators']
        self.assertEqual(len(collaborators), 3)
        expected_fields = {'hasEditPermissions', 'hasViewPermissions'}
        expected_fields.update(USER_FIELDS)
        self.assertSetEqual(set(collaborators[0].keys()), expected_fields)
        self.assertEqual(collaborators[0]['email'], 'test@test.com')
        self.assertEqual(collaborators[0]['displayName'], '')
        self.assertFalse(collaborators[0]['isStaff'])
        self.assertTrue(collaborators[0]['hasViewPermissions'])
        self.assertFalse(collaborators[0]['hasEditPermissions'])

        username = collaborators[0]['username']
        user = User.objects.get(username=username)

        expected_email_content = """
    Hi there --

    Test Manager User has added you as a collaborator in seqr.

    Please click this link to set up your account:
    /users/set_password/{password_token}

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

        # get all project collaborators includes new collaborator
        get_all_collaborators_url = reverse(get_all_collaborators)
        response = self.client.get(get_all_collaborators_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {username, 'test_user_manager', 'test_user_non_staff'})
        self.assertSetEqual(set(response_json[username].keys()), USER_FIELDS)

        # calling create again just updates the existing user
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({
            'email': 'Test@test.com', 'firstName': 'Test', 'lastName': 'User'}))
        self.assertEqual(response.status_code, 200)
        collaborators = response.json()['projectsByGuid'][PROJECT_GUID]['collaborators']
        self.assertEqual(len(collaborators), 3)
        self.assertEqual(collaborators[2]['username'], username)
        self.assertEqual(collaborators[2]['displayName'], 'Test User')
        mock_send_mail.assert_not_called()

        # update the user
        update_url = reverse(update_project_collaborator, args=[PROJECT_GUID, username])
        response = self.client.post(update_url, content_type='application/json',  data=json.dumps(
            {'firstName': 'Edited', 'lastName': 'Collaborator', 'hasEditPermissions': True}))
        collaborators = response.json()['projectsByGuid'][PROJECT_GUID]['collaborators']
        self.assertEqual(len(collaborators), 3)
        self.assertEqual(collaborators[2]['email'], 'test@test.com')
        self.assertEqual(collaborators[2]['displayName'], 'Edited Collaborator')
        self.assertFalse(collaborators[2]['isStaff'])
        self.assertTrue(collaborators[2]['hasViewPermissions'])
        self.assertTrue(collaborators[2]['hasEditPermissions'])

        # delete the project collaborator
        delete_url = reverse(delete_project_collaborator, args=[PROJECT_GUID, username])
        response = self.client.post(delete_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        collaborators = response.json()['projectsByGuid'][PROJECT_GUID]['collaborators']
        self.assertEqual(len(collaborators), 2)

        # check that user still exists
        self.assertEqual(User.objects.filter(username=username).count(), 1)

    def test_set_password(self):
        username = 'test_new_user'
        user = User.objects.create_user(username)
        password = user.password
        auth_user = auth.get_user(self.client)
        self.assertNotEqual(user, auth_user)

        set_password_url = reverse(set_password, args=[username])
        response = self.client.post(set_password_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Password is required')

        response = self.client.post(set_password_url, content_type='application/json', data=json.dumps({
            'password': 'password123', 'firstName': 'Test'}))
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username='test_new_user')
        self.assertEqual(user.first_name, 'Test')
        self.assertFalse(user.password == password)

        auth_user = auth.get_user(self.client)
        self.assertEqual(user, auth_user)

    @mock.patch('django.contrib.auth.models.send_mail')
    def test_forgot_password(self, mock_send_mail):
        url = reverse(forgot_password)

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
            'email': 'test_user@test.com'
        }))
        self.assertEqual(response.status_code, 200)

        expected_email_content = """
        Hi there Test User--

        Please click this link to reset your seqr password:
        /users/set_password/pbkdf2_sha256%2430000%24y85kZgvhQ539%24jrEC3L1IhCezUx3Itp%2B14w%2FT7U6u5XUxtpBZXKv8eh4%3D?reset=true
        """
        mock_send_mail.assert_called_with(
            'Reset your seqr password',
            expected_email_content,
            None,
            ['test_user@test.com'],
            fail_silently=False,
        )

        # Test email failure
        mock_send_mail.side_effect = AnymailError('Connection err')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'email': 'test_user@test.com'
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Connection err')

    def test_update_policies(self):
        self.assertEqual(UserPolicy.objects.filter(user=self.no_access_user).count(), 0)

        url = reverse(update_policies)
        self.check_require_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'User must accept current policies')

        response = self.client.post(url, content_type='application/json', data=json.dumps({'acceptedPolicies': True}))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'currentPolicies': True})

        new_policy = UserPolicy.objects.get(user=self.no_access_user)
        self.assertEqual(new_policy.privacy_version, SEQR_PRIVACY_VERSION)
        self.assertEqual(new_policy.tos_version, SEQR_TOS_VERSION)

        # Test updating user with out of date policies
        existing_policy = UserPolicy.objects.get(user=self.manager_user)
        self.assertNotEqual(existing_policy.privacy_version, SEQR_PRIVACY_VERSION)
        self.assertNotEqual(existing_policy.tos_version, SEQR_TOS_VERSION)

        self.login_manager()
        response = self.client.post(url, content_type='application/json', data=json.dumps({'acceptedPolicies': True}))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'currentPolicies': True})

        existing_policy = UserPolicy.objects.get(user=self.manager_user)
        self.assertEqual(existing_policy.privacy_version, SEQR_PRIVACY_VERSION)
        self.assertEqual(existing_policy.tos_version, SEQR_TOS_VERSION)
