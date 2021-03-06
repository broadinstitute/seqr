import json
import mock

from django.urls.base import reverse

from seqr.views.apis.dashboard_api import dashboard_page_data, export_projects_table_handler
from seqr.views.utils.terra_api_utils import TerraAPIException
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, MixAuthenticationTestCase,\
    PROJECT_FIELDS

PROJECT_EXPORT_HEADER = [
    'Project',
    'Description',
    'Categories',
    'Created Date',
    'Families',
    'Individuals',
    'Tagged Variants',
    'WES Samples',
    'WGS Samples',
    'RNA Samples',
    'Solved - known gene for phenotype',
    'Solved - gene linked to different phenotype',
    'Solved - novel gene', 'Strong candidate - known gene for phenotype',
    'Strong candidate - gene linked to different phenotype',
    'Strong candidate - novel gene',
    'Reviewed, currently pursuing candidates',
    'Reviewed, no clear candidate',
    'Closed, no longer under analysis',
    'Analysis in Progress',
    'Waiting for data',
]

DASHBOARD_PROJECT_FIELDS = {
    'numIndividuals', 'numFamilies', 'sampleTypeCounts', 'numVariantTags', 'analysisStatusCounts',
}
DASHBOARD_PROJECT_FIELDS.update(PROJECT_FIELDS)

class DashboardPageTest(object):

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP', 'analysts')
    def test_dashboard_page_data(self):
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

        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['projectsByGuid']), 3)

        if hasattr(self, 'mock_list_workspaces'):
            self.mock_list_workspaces.side_effect = TerraAPIException('AnVIL Error', 400)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error'], 'AnVIL Error')

        self.login_data_manager_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['projectsByGuid']), 4)

    @mock.patch('seqr.views.utils.orm_to_json_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    def test_export_projects_table(self):
        url = reverse(export_projects_table_handler)
        self.check_require_login(url)

        response = self.client.get('{}?file_format=tsv'.format(url))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), 'text/tsv')
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="projects.tsv"')
        # authenticated user has access to no projects so should be empty export
        export_content = [row.split('\t') for row in response.content.decode('utf-8').rstrip('\n').split('\n')]
        self.assertListEqual(export_content, [PROJECT_EXPORT_HEADER])

        # test with access to data
        self.login_collaborator()
        response = self.client.get('{}?file_format=tsv'.format(url))
        self.assertEqual(response.status_code, 200)
        export_content = [row.split('\t') for row in response.content.decode('utf-8').rstrip('\n').split('\n')]
        self.assertEqual(len(export_content), self.NUM_COLLABORATOR_PROJECTS + 1)
        self.assertListEqual(export_content[0], PROJECT_EXPORT_HEADER)
        self.assertListEqual(
            export_content[1],
            ['1kg project n\u00e5me with uni\u00e7\u00f8de',
             '1000 genomes project description with uni\u00e7\u00f8de',
             'CMG, c\u00e5teg\u00f8ry with uni\u00e7\u00f8de',
             '2017-03-12 19:27:08.156000+00:00', '11', '14', '4', '14', '0', '0', '0', '0', '0', '0', '0', '0', '0',
             '0', '0', '0', '11'],
        )

        response = self.client.get('{}?file_format=xls'.format(url))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), 'application/ms-excel')
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="projects.xlsx"')

        response = self.client.get('{}?file_format=json'.format(url))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), 'application/json')
        self.assertEqual(response.get('Content-Disposition'), 'attachment; filename="projects.json"')
        export_content = [json.loads(row) for row in response.content.decode('utf-8').rstrip('\n').split('\n')]
        self.assertEqual(len(export_content), self.NUM_COLLABORATOR_PROJECTS)
        self.assertDictEqual(export_content[0], {
            'project': '1kg project n\u00e5me with uni\u00e7\u00f8de',
            'description': '1000 genomes project description with uni\u00e7\u00f8de',
            'categories': 'CMG, c\u00e5teg\u00f8ry with uni\u00e7\u00f8de',
            'created_date': '2017-03-12 19:27:08.156000+00:00', 'families': '11', 'individuals': '14',
            'tagged_variants': '4', 'wes_samples': '14', 'wgs_samples': '0', 'rna_samples': '0',
            'solved_-_known_gene_for_phenotype': '0', 'closed,_no_longer_under_analysis': '0',
            'analysis_in_progress': '0', 'strong_candidate_-_gene_linked_to_different_phenotype': '0',
            'solved_-_novel_gene': '0', 'reviewed,_currently_pursuing_candidates': '0',
            'solved_-_gene_linked_to_different_phenotype': '0', 'reviewed,_no_clear_candidate': '0',
            'strong_candidate_-_novel_gene': '0', 'strong_candidate_-_known_gene_for_phenotype': '0',
            'waiting_for_data': '11'
        })

        response = self.client.get('{}?file_format=csv'.format(url))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Invalid file_format: csv'})


# Tests for AnVIL access disabled
class LocalDashboardPageTest(AuthenticationTestCase, DashboardPageTest):
    fixtures = ['users', '1kg_project']
    NUM_COLLABORATOR_PROJECTS = 3


def assert_has_list_workspaces_calls(self, call_count=4):
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

    def test_dashboard_page_data(self):
        super(AnvilDashboardPageTest, self).test_dashboard_page_data()
        assert_has_anvil_calls(self)

    def test_export_projects_table(self):
        super(AnvilDashboardPageTest, self).test_export_projects_table()
        assert_has_list_workspaces_calls(self, call_count=5)
        self.mock_get_ws_acl.assert_not_called()


# Test for permissions from AnVIL and local
class MixDashboardPageTest(MixAuthenticationTestCase, DashboardPageTest):
    fixtures = ['users', 'social_auth', '1kg_project']
    NUM_COLLABORATOR_PROJECTS = 3

    def test_dashboard_page_data(self):
        super(MixDashboardPageTest, self).test_dashboard_page_data()
        assert_has_anvil_calls(self)

    def test_export_projects_table(self):
        super(MixDashboardPageTest, self).test_export_projects_table()
        assert_has_list_workspaces_calls(self, call_count=5)
        self.mock_get_ws_acl.assert_not_called()
