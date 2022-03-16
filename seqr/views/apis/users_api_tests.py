import json
import mock

from anymail.exceptions import AnymailError
from django.contrib import auth
from django.contrib.auth.models import User
from django.urls.base import reverse
from urllib.parse import quote_plus

from seqr.models import UserPolicy, Project

from seqr.views.apis.users_api import get_all_collaborator_options, set_password, \
    create_project_collaborator, update_project_collaborator, delete_project_collaborator, forgot_password, \
    get_project_collaborator_options, update_policies, update_user
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase,\
    MixAuthenticationTestCase, USER_FIELDS


PROJECT_GUID = "R0001_1kg"
NON_ANVIL_PROJECT_GUID = "R0002_empty"
USERNAME = "test_user_collaborator"
USER_OPTION_FIELDS = {
    "displayName",
    "firstName",
    "lastName",
    "username",
    "email",
    "isAnalyst",
}
ANALYST_USERNAME = "test_user"

TOS_VERSION = 2.2
PRIVACY_VERSION = 1.1


class UsersAPITest(object):
    USERNAME = USERNAME

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP', 'analysts')
    @mock.patch('seqr.views.utils.orm_to_json_utils.ANALYST_USER_GROUP')
    def test_get_project_collaborator_options(self, mock_analyst_group):
        url = reverse(get_project_collaborator_options, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        if hasattr(self, 'mock_get_ws_acl'):
            self.mock_get_ws_acl.reset_mock()
            self.mock_get_ws_access_level.reset_mock()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), self.COLLABORATOR_NAMES)
        self.assertSetEqual(set(response_json['test_user_manager'].keys()), USER_OPTION_FIELDS)

        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        users = {ANALYST_USERNAME, 'test_pm_user'}
        users.update(self.COLLABORATOR_NAMES)
        self.assertSetEqual(set(response_json.keys()), users)
        self.assertSetEqual(set(response_json[ANALYST_USERNAME].keys()), USER_OPTION_FIELDS)
        self.assertTrue(response_json[ANALYST_USERNAME]['isAnalyst'])

    def test_get_all_collaborator_options(self):
        url = reverse(get_all_collaborator_options)
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(list(response.json().keys()), [])

        self.login_collaborator()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), self.LOCAL_COLLABORATOR_NAMES)
        if self.LOCAL_COLLABORATOR_NAMES:
            self.assertSetEqual(
                set(response_json["test_user_manager"].keys()), USER_OPTION_FIELDS
            )

    def test_create_anvil_project_collaborator(self):
        create_url = reverse(create_project_collaborator, args=[PROJECT_GUID])
        self.check_manager_login(create_url)

        response = self.client.post(
            create_url, content_type="application/json", data=json.dumps({})
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

    @mock.patch("seqr.views.apis.users_api.logger")
    @mock.patch("django.contrib.auth.models.send_mail")
    def test_create_project_collaborator(self, mock_send_mail, mock_logger):
        create_url = reverse(create_project_collaborator, args=[NON_ANVIL_PROJECT_GUID])
        self.check_manager_login(create_url)

        # send invalid request
        response = self.client.post(
            create_url, content_type="application/json", data=json.dumps({})
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Email is required")

        # create
        response = self.client.post(
            create_url,
            content_type="application/json",
            data=json.dumps({"email": "test@test.com", "firstName": "Test"}),
        )
        self.assertEqual(response.status_code, 200)
        collaborators = response.json()["projectsByGuid"][NON_ANVIL_PROJECT_GUID][
            "collaborators"
        ]
        self.assertEqual(len(collaborators), len(self.LOCAL_COLLABORATOR_NAMES) + 1)
        expected_fields = {"hasEditPermissions", "hasViewPermissions"}
        expected_fields.update(USER_FIELDS)
        self.assertSetEqual(set(collaborators[0].keys()), expected_fields)
        self.assertEqual(collaborators[0]["email"], "test@test.com")
        self.assertEqual(collaborators[0]["displayName"], "Test")
        self.assertFalse(collaborators[0]["isSuperuser"])
        self.assertFalse(collaborators[0]["isAnalyst"])
        self.assertFalse(collaborators[0]["isDataManager"])
        self.assertFalse(collaborators[0]["isPm"])
        self.assertTrue(collaborators[0]["hasViewPermissions"])
        self.assertFalse(collaborators[0]["hasEditPermissions"])

        username = collaborators[0]["username"]
        user = User.objects.get(username=username)

        expected_email_content = """
    Hi there Test--

    Test Manager User has added you as a collaborator in seqr.

    {setup_message}

    Thanks!
    """.format(
            setup_message=self.EMAIL_SETUP_MESSAGE.format(password_token=user.password)
        )
        mock_send_mail.assert_called_with(
            "Set up your seqr account",
            expected_email_content,
            None,
            ["test@test.com"],
            fail_silently=False,
        )
        mock_send_mail.reset_mock()

        mock_logger.info.assert_called_with(
            "Created user test@test.com (local)", self.manager_user
        )
        mock_logger.reset_mock()

        # check user object added to project set
        self.assertEqual(
            Project.objects.get(guid=NON_ANVIL_PROJECT_GUID)
            .can_view_group.user_set.filter(username=username)
            .count(),
            1,
        )

        # calling create again just updates the existing user
        response = self.client.post(
            create_url,
            content_type="application/json",
            data=json.dumps(
                {
                    "email": "Test@test.com",
                    "firstName": "Test",
                    "lastName": "Invalid Name Update",
                }
            ),
        )
        self.assertEqual(response.status_code, 200)
        collaborators = response.json()["projectsByGuid"][NON_ANVIL_PROJECT_GUID][
            "collaborators"
        ]
        self.assertEqual(len(collaborators), len(self.LOCAL_COLLABORATOR_NAMES) + 1)
        new_collab = next(
            collab for collab in collaborators if collab["email"] == "test@test.com"
        )
        self.assertEqual(new_collab["username"], username)
        self.assertEqual(new_collab["displayName"], "Test")
        mock_send_mail.assert_not_called()
        mock_logger.info.assert_not_called()

        # Test email failure
        mock_send_mail.side_effect = AnymailError("Connection err")
        response = self.client.post(
            create_url,
            content_type="application/json",
            data=json.dumps({"email": "Test_new@test.com"}),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Connection err")

    def _test_update_user(self, username, can_edit=True, check_access=True):
        update_url = reverse(update_project_collaborator, args=[PROJECT_GUID, username])
        if check_access:
            self.check_manager_login(update_url)

        response = self.client.post(
            update_url,
            content_type="application/json",
            data=json.dumps(
                {
                    "firstName": "Edited",
                    "lastName": "Collaborator",
                    "hasEditPermissions": True,
                }
            ),
        )
        collaborators = response.json()["projectsByGuid"][PROJECT_GUID]["collaborators"]
        self.assertEqual(len(collaborators), len(self.COLLABORATOR_NAMES))
        edited_collab = next(
            collab for collab in collaborators if collab["username"] == username
        )
        self.assertNotEqual(edited_collab["displayName"], "Edited Collaborator")
        self.assertFalse(edited_collab["isSuperuser"])
        self.assertTrue(edited_collab["hasViewPermissions"])
        self.assertEqual(edited_collab["hasEditPermissions"], can_edit)

    def test_update_project_collaborator(self):
        self._test_update_user(self.USERNAME)

    def _test_delete_user(self, username, check_access=True, num_removed=1):
        delete_url = reverse(delete_project_collaborator, args=[PROJECT_GUID, username])
        if check_access:
            self.check_manager_login(delete_url)

        response = self.client.post(delete_url, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        collaborators = response.json()["projectsByGuid"][PROJECT_GUID]["collaborators"]
        self.assertEqual(len(collaborators), len(self.COLLABORATOR_NAMES) - num_removed)

        # check that user still exists
        self.assertEqual(User.objects.filter(username=username).count(), 1)

    def test_delete_project_collaborator(self):
        self._test_delete_user(self.USERNAME)

    def _test_password_auth_disabled(self, url):
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

    @mock.patch("seqr.views.apis.users_api.SEQR_TOS_VERSION")
    @mock.patch("seqr.views.apis.users_api.SEQR_PRIVACY_VERSION")
    def test_update_policies(self, mock_privacy, mock_tos):
        mock_privacy.resolve_expression.return_value = PRIVACY_VERSION
        mock_tos.resolve_expression.return_value = TOS_VERSION
        self.assertEqual(UserPolicy.objects.filter(user=self.no_policy_user).count(), 0)

        url = reverse(update_policies)
        self.check_require_login_no_policies(url)

        response = self.client.post(
            url, content_type="application/json", data=json.dumps({})
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, "User must accept current policies")

        response = self.client.post(
            url,
            content_type="application/json",
            data=json.dumps({"acceptedPolicies": True}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {"currentPolicies": True})

        new_policy = UserPolicy.objects.get(user=self.no_policy_user)
        self.assertEqual(new_policy.privacy_version, PRIVACY_VERSION)
        self.assertEqual(new_policy.tos_version, TOS_VERSION)

        # Test updating user with out of date policies
        mock_privacy.resolve_expression.return_value = PRIVACY_VERSION + 1
        mock_tos.resolve_expression.return_value = TOS_VERSION + 2

        response = self.client.post(
            url,
            content_type="application/json",
            data=json.dumps({"acceptedPolicies": True}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {"currentPolicies": True})

        existing_policy = UserPolicy.objects.get(user=self.no_policy_user)
        self.assertEqual(existing_policy.privacy_version, PRIVACY_VERSION + 1)
        self.assertEqual(existing_policy.tos_version, TOS_VERSION + 2)

    def test_update_user(self):
        url = reverse(update_user)
        self.check_require_login(url)

        response = self.client.post(
            url,
            content_type="application/json",
            data=json.dumps(
                {
                    "email": "Test@test.com",
                    "firstName": "New",
                    "lastName": "Username",
                    "isSuperuser": True,
                }
            ),
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), USER_FIELDS)
        self.assertEqual(response_json["firstName"], "New")
        self.assertEqual(response_json["lastName"], "Username")
        self.assertEqual(response_json["displayName"], "New Username")
        self.assertEqual(response_json["email"], "test_user_no_access@test.com")
        self.assertFalse(response_json["isSuperuser"])


# Tests for AnVIL access disabled
class LocalUsersAPITest(AuthenticationTestCase, UsersAPITest):
    fixtures = ["users", "1kg_project"]
    COLLABORATOR_NAMES = {"test_user_manager", "test_user_collaborator"}
    LOCAL_COLLABORATOR_NAMES = COLLABORATOR_NAMES
    EMAIL_SETUP_MESSAGE = "Please click this link to set up your account:\n    /login/set_password/{password_token}"


class AnvilUsersAPITest(AnvilAuthenticationTestCase, UsersAPITest):
    fixtures = ["users", "social_auth", "1kg_project"]
    COLLABORATOR_NAMES = {
        "test_user_manager",
        "test_user_collaborator",
        "test_user_pure_anvil@test.com",
    }
    LOCAL_COLLABORATOR_NAMES = set()

    def test_get_all_collaborator_options(self):
        super(AnvilUsersAPITest, self).test_get_all_collaborator_options()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_ws_access_level.assert_not_called()

    def test_get_project_collaborator_options(self, *args, **kwargs):
        super(AnvilUsersAPITest, self).test_get_project_collaborator_options(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.assertEqual(self.mock_get_ws_acl.call_count, 2)
        self.mock_get_ws_acl.assert_called_with(
            self.collaborator_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.assertEqual(self.mock_get_ws_access_level.call_count, 2)
        self.mock_get_ws_access_level.assert_called_with(
            self.collaborator_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')

    def test_create_project_collaborator(self, *args):
        # Creating project collaborators is only allowed in non-anvil projects, so it always fails for the AnVIL only case
        create_url = reverse(create_project_collaborator, args=[NON_ANVIL_PROJECT_GUID])
        self.check_manager_login(create_url)

        response = self.client.post(
            create_url, content_type="application/json", data=json.dumps({})
        )
        self.assertEqual(response.status_code, 403)
        self.mock_get_ws_acl.assert_not_called()
        self.mock_list_workspaces.assert_not_called()

    def test_update_project_collaborator(self):
        self._test_update_user(USERNAME, can_edit=False)

        self.assertEqual(self.mock_get_ws_acl.call_count, 1)
        self.assertEqual(self.mock_get_ws_access_level.call_count, 2)

    def test_delete_project_collaborator(self):
        self._test_delete_user(USERNAME, num_removed=0)

        self.assertEqual(self.mock_get_ws_acl.call_count, 1)
        self.assertEqual(self.mock_get_ws_access_level.call_count, 2)

    def test_update_policies(self, *args, **kwargs):
        super(AnvilUsersAPITest, self).test_update_policies(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()


class MixUsersAPITest(MixAuthenticationTestCase, UsersAPITest):
    fixtures = ["users", "social_auth", "1kg_project"]
    LOCAL_COLLABORATOR_NAMES = {
        "test_user_manager",
        "test_user_collaborator",
        "test_local_user",
    }
    COLLABORATOR_NAMES = {"test_user_pure_anvil@test.com"}
    COLLABORATOR_NAMES.update(LOCAL_COLLABORATOR_NAMES)
    USERNAME = "test_local_user"
    EMAIL_SETUP_MESSAGE = "You can now log into seqr using your Google account:\n    /login/google-oauth2"

    def test_get_all_collaborator_options(self):
        super(MixUsersAPITest, self).test_get_all_collaborator_options()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_ws_access_level.assert_not_called()

    def test_get_project_collaborator_options(self, *args, **kwargs):
        super(MixUsersAPITest, self).test_get_project_collaborator_options(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_access_level.assert_not_called()
        self.assertEqual(self.mock_get_ws_acl.call_count, 2)
        self.mock_get_ws_acl.assert_called_with(
            self.collaborator_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')

    def test_create_project_collaborator(self, *args, **kwargs):
        super(MixUsersAPITest, self).test_create_project_collaborator(*args, **kwargs)
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_ws_access_level.assert_not_called()

    def test_update_project_collaborator(self):
        super(MixUsersAPITest, self).test_update_project_collaborator()
        self._test_update_user(USERNAME, can_edit=False, check_access=False)

        self.assertEqual(self.mock_get_ws_acl.call_count, 2)
        self.mock_get_ws_access_level.assert_called_with(
            self.collaborator_user,
            "my-seqr-billing",
            "anvil-1kg project n\u00e5me with uni\u00e7\u00f8de",
        )

    def test_delete_project_collaborator(self):
        super(MixUsersAPITest, self).test_delete_project_collaborator()
        self._test_delete_user(USERNAME, check_access=False)

        self.assertEqual(self.mock_get_ws_acl.call_count, 2)
        self.mock_get_ws_access_level.assert_called_with(
            self.collaborator_user,
            "my-seqr-billing",
            "anvil-1kg project n\u00e5me with uni\u00e7\u00f8de",
        )

    def test_update_policies(self, *args, **kwargs):
        super(MixUsersAPITest, self).test_update_policies(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
