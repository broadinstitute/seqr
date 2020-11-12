import mock
from django.urls.base import reverse
from seqr.views.apis.awesomebar_api import awesomebar_autocomplete_handler
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, MixAuthenticationTestCase,\
    WORKSPACE_FIELDS


class AwesomebarAPITest(object):
    multi_db = True

    def test_awesomebar_autocomplete_handler(self):
        url = reverse(awesomebar_autocomplete_handler)
        self.check_require_login(url)

        response = self.client.get(url + "?q=")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'matches': {}})

        response = self.client.get(url+"?q=1")
        self.assertEqual(response.status_code, 200)
        # No objects returned as user has no access
        self.assertSetEqual(
            set(response.json()['matches'].keys()), {'genes'}
        )

        self.login_collaborator()
        response = self.client.get(url + "?q=1")
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(
            set(response.json()['matches'].keys()), {'projects', 'families', 'analysis_groups', 'individuals', 'genes'}
        )

        response = self.client.get(url + "?q=T&categories=project_groups,projects,hpo_terms,omim")
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json()['matches'].keys()), {'projects', 'project_groups', 'omim', 'hpo_terms'})


# Tests for AnVIL access disabled
class LocalAwesomebarAPITest(AuthenticationTestCase, AwesomebarAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']


# Test for permissions from AnVIL only
class AnvilAwesomebarAPITest(AnvilAuthenticationTestCase, AwesomebarAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']

    def test_awesomebar_autocomplete_handler(self):
        super(AnvilAwesomebarAPITest, self).test_awesomebar_autocomplete_handler()
        calls = [
            mock.call(self.no_access_user, fields=WORKSPACE_FIELDS),
            mock.call(self.collaborator_user, fields=WORKSPACE_FIELDS),
            mock.call(self.collaborator_user, fields=WORKSPACE_FIELDS),
        ]
        self.mock_list_workspaces.assert_has_calls(calls)
        self.mock_service_account.get.assert_not_called()


# Test for permissions from AnVIL and local
class MixAwesomebarAPITest(MixAuthenticationTestCase, AwesomebarAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']

    def test_awesomebar_autocomplete_handler(self):
        super(MixAwesomebarAPITest, self).test_awesomebar_autocomplete_handler()
        calls = [
            mock.call(self.no_access_user, fields=WORKSPACE_FIELDS),
            mock.call(self.collaborator_user, fields=WORKSPACE_FIELDS),
            mock.call(self.collaborator_user, fields=WORKSPACE_FIELDS),
        ]
        self.mock_list_workspaces.assert_has_calls(calls)
        self.mock_service_account.get.assert_not_called()
