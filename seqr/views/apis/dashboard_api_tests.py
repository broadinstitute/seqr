import mock

from django.urls.base import reverse

from seqr.views.apis.dashboard_api import dashboard_page_data
from seqr.views.utils.terra_api_utils import TerraAPIException
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, MixAuthenticationTestCase,\
    PROJECT_FIELDS
from seqr.models import Project

DASHBOARD_PROJECT_FIELDS = {
    'numIndividuals', 'numFamilies', 'sampleTypeCounts', 'numVariantTags', 'analysisStatusCounts',
}
DASHBOARD_PROJECT_FIELDS.update(PROJECT_FIELDS)

@mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json')
class DashboardPageTest(object):

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP', 'analysts')
    @mock.patch('seqr.views.utils.permissions_utils.safe_redis_set_json')
    def test_dashboard_page_data(self, mock_set_redis, mock_get_redis):
        mock_get_redis.return_value = None
        url = reverse(dashboard_page_data)
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'projectsByGuid': {}, 'projectCategoriesByGuid': {}})

        self.login_collaborator()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'projectsByGuid', 'projectCategoriesByGuid'})
        self.assertSetEqual(
            set(next(iter(response_json['projectCategoriesByGuid'].values())).keys()),
            {'created_by_id', 'created_date', 'guid', 'id', 'last_modified_date', 'name'}
        )
        self.assertEqual(len(response_json['projectsByGuid']), self.NUM_COLLABORATOR_PROJECTS)
        self.assertSetEqual(
            set(next(iter(response_json['projectsByGuid'].values())).keys()), DASHBOARD_PROJECT_FIELDS
        )
        mock_get_redis.assert_called_with('projects__test_user_collaborator')
        mock_set_redis.assert_called_with(
            'projects__test_user_collaborator', list(response_json['projectsByGuid'].keys()), expire=300)

        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['projectsByGuid']), 3)

        self.login_data_manager_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['projectsByGuid']), 4)

        mock_get_redis.return_value = ['R0001_1kg']
        mock_set_redis.reset_mock()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json()['projectsByGuid'].keys()), {'R0001_1kg'})
        mock_get_redis.assert_called_with('projects__test_data_manager')
        mock_set_redis.assert_not_called()

        # Test all user projects
        mock_get_redis.return_value = None
        Project.objects.update(all_user_demo=True)
        self.login_base_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        project_json = response.json()['projectsByGuid']
        self.assertSetEqual(set(project_json.keys()), {'R0003_test'})
        self.assertFalse(project_json['R0003_test']['canEdit'])
        self.assertFalse(project_json['R0003_test']['isMmeEnabled'])

        if hasattr(self, 'mock_list_workspaces'):
            self.mock_list_workspaces.side_effect = TerraAPIException('AnVIL Error', 400)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error'], 'AnVIL Error')

# Tests for AnVIL access disabled
class LocalDashboardPageTest(AuthenticationTestCase, DashboardPageTest):
    fixtures = ['users', '1kg_project']
    NUM_COLLABORATOR_PROJECTS = 3


def assert_has_list_workspaces_calls(self, call_count=5):
    self.assertEqual(self.mock_list_workspaces.call_count, call_count)
    calls = [
        mock.call(self.no_access_user),
        mock.call(self.collaborator_user),
    ]
    self.mock_list_workspaces.assert_has_calls(calls)

def assert_has_anvil_calls(self):
    assert_has_list_workspaces_calls(self)
    calls = [
        mock.call(self.collaborator_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de'),
        mock.call(self.collaborator_user, 'my-seqr-billing', 'anvil-project 1000 Genomes Demo')
    ]
    self.mock_get_ws_access_level.assert_has_calls(calls, any_order=True)
    self.mock_get_ws_acl.assert_not_called()


# Test for permissions from AnVIL only
class AnvilDashboardPageTest(AnvilAuthenticationTestCase, DashboardPageTest):
    fixtures = ['users', 'social_auth', '1kg_project']
    NUM_COLLABORATOR_PROJECTS = 2

    def test_dashboard_page_data(self, *args):
        super(AnvilDashboardPageTest, self).test_dashboard_page_data(*args)
        assert_has_anvil_calls(self)


# Test for permissions from AnVIL and local
class MixDashboardPageTest(MixAuthenticationTestCase, DashboardPageTest):
    fixtures = ['users', 'social_auth', '1kg_project']
    NUM_COLLABORATOR_PROJECTS = 3

    def test_dashboard_page_data(self, *args):
        super(MixDashboardPageTest, self).test_dashboard_page_data(*args)
        assert_has_anvil_calls(self)
