import mock

from django.urls.base import reverse

from seqr.views.apis.dashboard_api import dashboard_page_data
from seqr.views.utils.terra_api_utils import TerraAPIException
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, PROJECT_FIELDS
from seqr.models import Project

DASHBOARD_PROJECT_FIELDS = {
    'numIndividuals', 'numFamilies', 'sampleTypeCounts', 'numVariantTags', 'analysisStatusCounts',
}
DASHBOARD_PROJECT_FIELDS.update(PROJECT_FIELDS)
DASHBOARD_PROJECT_FIELDS.remove('canEdit')

EXPECTED_DASHBOARD_PROJECT = {
    'numIndividuals': 14,
    'numFamilies': 11,
    'sampleTypeCounts': {'RNA': 2, 'WES': 13},
    'numVariantTags': 4,
    'analysisStatusCounts': {'ES': 1, 'Q': 9, 'S_ng': 1},
    **{k: mock.ANY for k in PROJECT_FIELDS if k != 'canEdit'},
}


@mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json')
class DashboardPageTest(object):

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
        self.assertSetEqual({p['userIsCreator'] for p in response_json['projectsByGuid'].values()}, {False})
        self.assertFalse(any('userCanDelete' in p for p in response_json['projectsByGuid'].values()))
        self.assertDictEqual(response_json['projectsByGuid']['R0001_1kg'], EXPECTED_DASHBOARD_PROJECT)
        mock_get_redis.assert_called_with('projects__test_user_collaborator')
        mock_set_redis.assert_called_with(
            'projects__test_user_collaborator', list(response_json['projectsByGuid'].keys()), expire=300)

        self.login_manager()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(len(response_json['projectsByGuid']), 4)
        self.assertTrue(response_json['projectsByGuid']['R0002_empty']['userIsCreator'])
        self.assertTrue(response_json['projectsByGuid']['R0004_non_analyst_project']['userIsCreator'])
        self.assertFalse(response_json['projectsByGuid']['R0001_1kg']['userIsCreator'])
        self.assertTrue(response_json['projectsByGuid']['R0003_test']['userIsCreator'])
        self.assertTrue(response_json['projectsByGuid']['R0002_empty']['userCanDelete'])
        self.assertFalse(response_json['projectsByGuid']['R0004_non_analyst_project']['userCanDelete'])

        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(len(response_json['projectsByGuid']), 3)
        self.assertFalse(response_json['projectsByGuid']['R0002_empty']['userIsCreator'])
        self.assertTrue(response_json['projectsByGuid']['R0001_1kg']['userIsCreator'])
        self.assertFalse(response_json['projectsByGuid']['R0003_test']['userIsCreator'])
        mock_get_redis.assert_called_with('projects__test_user')
        mock_set_redis.assert_called_with('projects__test_user', list(response_json['projectsByGuid'].keys()), expire=300)

        mock_get_redis.return_value = ['R0001_1kg']
        mock_set_redis.reset_mock()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json()['projectsByGuid'].keys()), {'R0001_1kg'})
        mock_get_redis.assert_called_with('projects__test_user')
        mock_set_redis.assert_not_called()

        mock_get_redis.reset_mock()
        mock_set_redis.reset_mock()
        self.login_data_manager_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['projectsByGuid']), 4)
        mock_get_redis.assert_not_called()
        mock_set_redis.assert_not_called()

        # Test all user projects
        mock_get_redis.return_value = None
        Project.objects.update(all_user_demo=True)
        self.login_base_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        project_json = response.json()['projectsByGuid']
        self.assertSetEqual(set(project_json.keys()), {'R0003_test'})
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


def assert_has_list_workspaces_calls(self, call_count=6):
    self.assertEqual(self.mock_list_workspaces.call_count, call_count)
    calls = [
        mock.call(self.no_access_user),
        mock.call(self.collaborator_user),
    ]
    self.mock_list_workspaces.assert_has_calls(calls)

def assert_has_anvil_calls(self):
    assert_has_list_workspaces_calls(self)
    self.mock_get_ws_access_level.assert_not_called()
    self.assert_no_extra_anvil_calls()


# Test for permissions from AnVIL only
class AnvilDashboardPageTest(AnvilAuthenticationTestCase, DashboardPageTest):
    fixtures = ['users', 'social_auth', '1kg_project']
    NUM_COLLABORATOR_PROJECTS = 2

    def test_dashboard_page_data(self, *args):
        super(AnvilDashboardPageTest, self).test_dashboard_page_data(*args)
        assert_has_anvil_calls(self)
