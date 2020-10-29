import json
import responses
import mock

from django.urls.base import reverse

from settings import TERRA_API_ROOT_URL
from seqr.views.apis.dashboard_api import dashboard_page_data, export_projects_table_handler
from seqr.views.utils.terra_api_utils import anvil_enabled
from seqr.views.utils.test_utils import AuthenticationTestCase, GOOGLE_ACCESS_TOKEN_URL, GOOGLE_API_TOKEN_URL,\
    GOOGLE_SERVICE_ACCOUNT_INFO, GOOGLE_TOKEN_RESULT

WORKSPACE_FIELDS_URL = '{}api/workspaces?fields=public,workspace.name,workspace.namespace,workspace.workspaceId'.format(TERRA_API_ROOT_URL)
WORKSPACE_RSP_NO_VALID_PROJECT = '[{"public": false, "accessLevel": "PROJECT_OWNER", "workspace": {"name": "1000 Genomes Demo", "namespace": "my-seqr-billing", "workspaceId": "237998e6-663d-40b9-bd13-57c3bb6ac593" }}, {"accessLevel": "READER","workspace": {"name": "degenome","namespace": "degenome", "workspaceId": "2706d493-5fce-4fb2-9993-457c30364a06"}}, {"accessLevel": "PROJECT_OWNER","workspace": {"name": "seqr-project 1000 Genomes Demo","namespace": "my-seqr-billing","workspaceId": "6a048145-c134-4004-a009-42824f826ee8"}}]'
WORKSPACE_RSP_ONE_VALID_PROJECT = '[{"public": false, "accessLevel": "PROJECT_OWNER", "workspace": {"name": "1000 Genomes Demo", "namespace": "my-seqr-billing", "workspaceId": "237998e6-663d-40b9-bd13-57c3bb6ac593" }}, {"accessLevel": "READER","workspace": {"name": "degenome","namespace": "degenome", "workspaceId": "2706d493-5fce-4fb2-9993-457c30364a06"}}, {"public": false, "accessLevel": "PROJECT_OWNER","workspace": {"name": "seqr-project 1000 Genomes Demo","namespace": "my-seqr-billing","workspaceId": "6a048145-c134-4004-a009-42824f826ee8"}}]'
WORKSPACE_ACL_URL = '{}api/workspaces/my-seqr-billing/seqr-project%201000%20Genomes%20Demo/acl'.format(TERRA_API_ROOT_URL)
WORKSPACE_ACL_RSP = '{"acl": {"test_user@test.com": {"accessLevel": "OWNER","canCompute": true,"canShare": true,"pending": false},"sf-seqr@my-seqr.iam.gserviceaccount.com": {"accessLevel": "OWNER","canCompute": true,"canShare": true,"pending": false},"test2@test2.org": {"accessLevel": "OWNER","canCompute": true,"canShare": true,"pending": false},"test3@test3.com": {"accessLevel": "READER","canCompute": false,"canShare": false,"pending": false}}}'

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


@mock.patch('seqr.views.utils.terra_api_utils.GOOGLE_SERVICE_ACCOUNT_INFO', GOOGLE_SERVICE_ACCOUNT_INFO)
class DashboardPageTest(AuthenticationTestCase):
    if anvil_enabled():
        fixtures = ['users', 'social_auth_data', '1kg_project']
    else:
        fixtures = ['users', '1kg_project']

    @responses.activate
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
        self.assertEqual(len(response_json['projectsByGuid']), 2)
        self.assertSetEqual(
            set(next(iter(response_json['projectsByGuid'].values())).keys()),
            {'analysisStatusCounts', 'canEdit', 'createdDate', 'description', 'genomeVersion', 'sampleTypeCounts',
             'isMmeEnabled', 'lastAccessedDate', 'lastModifiedDate', 'projectCategoryGuids', 'projectGuid',
             'mmePrimaryDataOwner', 'mmeContactInstitution', 'mmeContactUrl', 'name', 'numFamilies', 'numIndividuals',
             'numVariantTags', 'workspaceName', 'workspaceNamespace'}
        )

        # Staff users can see all projects except those enabled "disable_staff_access"
        self.login_staff_user()
        responses.add(responses.POST, GOOGLE_ACCESS_TOKEN_URL, status=200, body=GOOGLE_TOKEN_RESULT)
        responses.add(responses.POST, GOOGLE_API_TOKEN_URL, status=200, body=GOOGLE_TOKEN_RESULT)
        responses.add(responses.GET, WORKSPACE_FIELDS_URL, status=200, body=WORKSPACE_RSP_NO_VALID_PROJECT)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['projectsByGuid']), 3)

        # Users can see the projects that AnVIL allows
        if anvil_enabled():
            responses.replace(responses.GET, WORKSPACE_FIELDS_URL, status=200, body=WORKSPACE_RSP_ONE_VALID_PROJECT)
            responses.add(responses.GET, WORKSPACE_ACL_URL, status=200, body=WORKSPACE_ACL_RSP)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()['projectsByGuid']), 4)
            self.maxDiff = None
            self.assertDictEqual(response.json()['projectsByGuid']['R0004_test'], {'canEdit': True, 'createdDate': '2017-03-12T19:27:08.156Z', 'description': '', 'genomeVersion': '37', 'isMmeEnabled': False, 'lastAccessedDate': '2017-09-15T18:15:50.827Z', 'lastModifiedDate': '2017-03-13T09:07:49.582Z', 'mmeContactInstitution': 'Broad Center for Mendelian Genomics', 'mmeContactUrl': 'mailto:seqr-test@gmail.com,test@broadinstitute.org', 'mmePrimaryDataOwner': '', 'name': 'Test AnVIL Project', 'numFamilies': 0, 'numIndividuals': 0, 'numVariantTags': 0, 'projectCategoryGuids': [], 'projectGuid': 'R0004_test', 'workspaceName': 'seqr-project 1000 Genomes Demo', 'workspaceNamespace': 'my-seqr-billing'})

    @responses.activate
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
        self.login_staff_user()
        responses.add(responses.POST, GOOGLE_ACCESS_TOKEN_URL, status=200, body=GOOGLE_TOKEN_RESULT)
        responses.add(responses.POST, GOOGLE_API_TOKEN_URL, status=200, body=GOOGLE_TOKEN_RESULT)
        responses.add(responses.GET, WORKSPACE_FIELDS_URL, status=200, body=WORKSPACE_RSP_NO_VALID_PROJECT)
        responses.add(responses.GET, WORKSPACE_ACL_URL, status=200, body=WORKSPACE_ACL_RSP)
        response = self.client.get('{}?file_format=tsv'.format(url))
        self.assertEqual(response.status_code, 200)
        export_content = [row.split('\t') for row in response.content.decode('utf-8').rstrip('\n').split('\n')]
        self.assertEqual(len(export_content), 4)
        self.assertListEqual(export_content[0], PROJECT_EXPORT_HEADER)
        self.assertListEqual(
            export_content[1],
            ['1kg project n\u00e5me with uni\u00e7\u00f8de',
             '1000 genomes project description with uni\u00e7\u00f8de',
             'c\u00e5teg\u00f8ry with uni\u00e7\u00f8de, test category name',
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
        self.assertEqual(len(export_content), 3)
        self.assertDictEqual(export_content[0], {
            'project': '1kg project n\u00e5me with uni\u00e7\u00f8de',
            'description': '1000 genomes project description with uni\u00e7\u00f8de',
            'categories': 'c\u00e5teg\u00f8ry with uni\u00e7\u00f8de, test category name',
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

        # Test for removed a project permitted by AnVIL
        if anvil_enabled():
            responses.replace(responses.GET, WORKSPACE_FIELDS_URL, status=200, body=WORKSPACE_RSP_ONE_VALID_PROJECT)
            response = self.client.get('{}?file_format=tsv'.format(url))
            self.assertEqual(response.status_code, 200)
            export_content = [row.split('\t') for row in response.content.decode('utf-8').rstrip('\n').split('\n')]
            self.assertEqual(len(export_content), 5)
