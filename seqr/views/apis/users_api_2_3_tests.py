from __future__ import unicode_literals

import json
import mock

from django.contrib import auth
from django.contrib.auth.models import User
from django.urls.base import reverse

from seqr.views.apis.users_api import get_all_collaborators, set_password, create_staff_user, \
    create_project_collaborator, update_project_collaborator, delete_project_collaborator, forgot_password, \
    get_all_staff
from seqr.views.utils.test_utils import AuthenticationTestCase


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

        self.assertSetEqual(
            set(first_staff_user),
            {'username', 'displayName', 'firstName', 'lastName', 'dateJoined', 'email', 'isStaff', 'lastLogin', 'id'}
        )
        self.assertTrue(first_staff_user['isStaff'])

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
        self.assertSetEqual(
            set(collaborators[0].keys()),
            {'dateJoined', 'email', 'firstName', 'isStaff', 'lastLogin', 'lastName', 'username', 'displayName',
             'hasViewPermissions', 'hasEditPermissions', 'id'}
        )
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
        self.assertSetEqual(
            set(response_json[username].keys()),
            {'dateJoined', 'email', 'firstName', 'isStaff', 'lastLogin', 'lastName', 'username', 'displayName', 'id'}
        )

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

    @mock.patch('django.contrib.auth.models.send_mail')
    def test_create_staff_user(self, mock_send_mail):
        create_url = reverse(create_staff_user)
        self.check_staff_login(create_url)

        # send invalid request
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Email is required')

        # create
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({
            'email': 'test_staff@test.com', 'firstName': 'Test', 'lastName': 'Staff'}))
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email='test_staff@test.com')
        self.assertTrue(user.is_staff)

        expected_email_content = """
    Hi there Test Staff--

    Test User has added you as a collaborator in seqr.

    Please click this link to set up your account:
    /users/set_password/{password_token}

    Thanks!
    """.format(password_token=user.password)
        mock_send_mail.assert_called_with(
            'Set up your seqr account',
            expected_email_content,
            None,
            ['test_staff@test.com'],
            fail_silently=False,
        )

        # calling create again fails
        response = self.client.post(create_url, content_type='application/json', data=json.dumps({
            'email': 'test_staff@test.com'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'This user already exists')

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

