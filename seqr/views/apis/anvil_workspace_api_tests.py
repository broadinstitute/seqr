from copy import deepcopy
import json
import mock
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.anvil_workspace_api import anvil_workspace_page, create_project_from_workspace
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, AuthenticationTestCase, TEST_WORKSPACE_NAMESPACE,\
    TEST_WORKSPACE_NAME, TEST_NO_PROJECT_WORKSPACE_NAME, TEST_NO_PROJECT_WORKSPACE_NAME2
from seqr.views.utils.terra_api_utils import remove_token, TerraAPIException, TerraRefreshTokenFailedException
from settings import SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL

LOAD_SAMPLE_DATA = [
    ["Family ID", "Individual ID", "Previous Individual ID", "Paternal ID", "Maternal ID", "Sex", "Affected Status",
     "Notes", "familyNotes"],
    ["1", "NA19675", "NA19675_1", "NA19678", "", "Female", "Affected", "A affected individual, test1-zsf", ""],
    ["1", "NA19678", "", "", "", "Male", "Unaffected", "a individual note", ""],
    ["21", "HG00735", "", "", "", "Female", "Unaffected", "", "a new family"]]

BAD_SAMPLE_DATA = [["1", "NA19674", "NA19674_1", "NA19678", "NA19679", "Female", "Affected", "A affected individual, test1-zsf", ""]]

REQUEST_BODY = {
    'genomeVersion': '38',
    'sampleType': 'WES',
    'uploadedFileId': 'test_temp_file_id',
    'description': 'A test project',
    'agreeSeqrAccess': True,
    'dataPath': '/test_path.vcf.gz'
}
REQUEST_BODY_NO_SLASH_DATA_PATH = deepcopy(REQUEST_BODY)
REQUEST_BODY_NO_SLASH_DATA_PATH['dataPath'] = 'test_no_slash_path.vcf.bgz'
REQUEST_BODY_BAD_DATA_PATH = deepcopy(REQUEST_BODY)
REQUEST_BODY_BAD_DATA_PATH['dataPath'] = 'test_path.vcf.tar'
REQUEST_BODY_VCF_DATA_PATH = deepcopy(REQUEST_BODY)
REQUEST_BODY_VCF_DATA_PATH['dataPath'] = 'test_path.vcf'
REQUEST_BODY_NO_AGREE_ACCESS = deepcopy(REQUEST_BODY)
REQUEST_BODY_NO_AGREE_ACCESS['agreeSeqrAccess'] = False

TEMP_PATH = '/temp_path/temp_filename'


@mock.patch('seqr.views.utils.permissions_utils.logger')
class AnvilWorkspaceAPITest(AnvilAuthenticationTestCase):
    fixtures = ['users', 'social_auth', '1kg_project']

    def test_anvil_workspace_page(self, mock_logger):
        # Requesting to load data from a workspace without an existing project
        url = reverse(anvil_workspace_page, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        collaborator_response = self.check_manager_login(url, login_redirect_url='/login/google-oauth2', policy_redirect_url='/accept_policies')

        mock_logger.warning.assert_called_with('User does not have sufficient permissions for workspace {}/{}'
                                               .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME),
                                               self.collaborator_user)
        self.assertEqual(collaborator_response.get('Content-Type'), 'text/html')
        initial_json = self.get_initial_page_json(collaborator_response)
        self.assertEqual(initial_json['user']['username'], 'test_user_collaborator')

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/create_project_from_workspace/{}/{}'.format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME))
        self.mock_get_ws_access_level.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)

        # Test error handling when token refresh fails
        self.mock_get_ws_access_level.side_effect = TerraRefreshTokenFailedException('Failed to refresh token')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            '/login/google-oauth2?next=/workspace/{}/{}'.format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)
        )
        self.mock_get_ws_access_level.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)

        # Requesting to load data for an existing project
        self.mock_get_ws_access_level.reset_mock()
        url = reverse(anvil_workspace_page, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/project/R0001_1kg/project_page')
        self.mock_get_ws_access_level.assert_not_called()

        # Test login locally
        remove_token(self.manager_user)  # The user will be same as logging in locally after the access token is removed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/workspace/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de')
        self.mock_get_ws_access_level.assert_not_called()

    @mock.patch('seqr.views.apis.anvil_workspace_api.BASE_URL', 'http://testserver/')
    @mock.patch('seqr.views.apis.anvil_workspace_api.time')
    @mock.patch('seqr.views.apis.anvil_workspace_api.logger')
    @mock.patch('seqr.views.apis.anvil_workspace_api.load_uploaded_file')
    @mock.patch('seqr.views.apis.anvil_workspace_api.has_service_account_access')
    @mock.patch('seqr.views.apis.anvil_workspace_api.add_service_account')
    @mock.patch('seqr.views.apis.anvil_workspace_api.safe_post_to_slack')
    @mock.patch('seqr.views.apis.anvil_workspace_api.does_file_exist')
    @mock.patch('seqr.views.apis.anvil_workspace_api.file_iter')
    @mock.patch('seqr.views.apis.anvil_workspace_api.mv_file_to_gs')
    @mock.patch('seqr.views.apis.anvil_workspace_api.tempfile.NamedTemporaryFile')
    def test_create_project_from_workspace(self, mock_tempfile, mock_mv_file, mock_file_iter, mock_file_exist, mock_slack, mock_add_service_account,
                                           mock_has_service_account, mock_load_file, mock_api_logger, mock_time,
                                           mock_utils_logger):
        # Requesting to load data from a workspace without an existing project
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')
        mock_utils_logger.warning.assert_called_with('User does not have sufficient permissions for workspace {}/{}'
                                               .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME),
                                               self.collaborator_user)

        # Test missing required fields in the request body
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Field(s) "genomeVersion, uploadedFileId, dataPath, sampleType" are required')
        self.mock_get_ws_access_level.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME, meta_fields=['workspace.bucketName'])

        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_NO_AGREE_ACCESS))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Must agree to grant seqr access to the data in the associated workspace.')

        # Test parsing sample data error
        mock_load_file.return_value = LOAD_SAMPLE_DATA + BAD_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertListEqual(response_json['errors'], ['NA19679 is the mother of NA19674 but doesn\'t have a separate record in the table'])

        # Test adding service account exception
        mock_load_file.return_value = LOAD_SAMPLE_DATA
        mock_add_service_account.side_effect = TerraAPIException('Failed to grant seqr service account access to the workspace {}/{}'
                                                                 .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME), 400)
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Failed to grant seqr service account access to the workspace {}/{}'
                              .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME))

        # Test adding service account never processes
        mock_add_service_account.reset_mock(side_effect=True)
        mock_add_service_account.return_value = True
        mock_has_service_account.return_value = False
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Failed to grant seqr service account access to the workspace')
        mock_has_service_account.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)
        self.assertEqual(mock_has_service_account.call_count, 3)
        self.assertEqual(mock_time.sleep.call_count, 3)

        # Test bad data path
        mock_time.reset_mock()
        mock_has_service_account.reset_mock()
        mock_has_service_account.return_value = True
        mock_file_exist.return_value = False
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_NO_SLASH_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Data file or path test_no_slash_path.vcf.bgz is not found.')
        mock_file_exist.assert_called_with('gs://test_bucket/test_no_slash_path.vcf.bgz', user=self.manager_user)
        mock_has_service_account.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)
        self.assertEqual(mock_has_service_account.call_count, 1)
        self.assertEqual(mock_time.sleep.call_count, 1)

        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(REQUEST_BODY_BAD_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid VCF file format - file path must end with .vcf, .vcf.gz, or .vcf.bgz')

        mock_file_exist.return_value = True
        mock_file_iter.return_value = ['##fileformat=VCFv4.2\n', '#CHROM	POS	ID	REF	ALT	QUAL']  # incomplete header line
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'No samples found in the provided VCF. This may be due to a malformed file')
        mock_file_iter.assert_called_with('gs://test_bucket/test_path.vcf.gz', byte_range=(0, 65536))
        mock_file_exist.assert_called_with('gs://test_bucket/test_path.vcf.gz', user=self.manager_user)

        # Test valid operation
        mock_time.reset_mock()
        mock_file_exist.reset_mock()
        mock_file_iter.reset_mock()
        mock_has_service_account.reset_mock()
        mock_add_service_account.return_value = False
        mock_file_exist.return_value = True
        mock_file_iter.return_value = ['##fileformat=VCFv4.2\n', '#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	NA19675	NA19678	HG00735\n',
                                       'chr1	1000	test\n']
        mock_tempfile.return_value.__enter__.return_value.name = TEMP_PATH
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_VCF_DATA_PATH))
        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(workspace_namespace=TEST_WORKSPACE_NAMESPACE, workspace_name=TEST_NO_PROJECT_WORKSPACE_NAME)
        response_json = response.json()
        self.assertEqual(project.guid, response_json['projectGuid'])
        self.assertListEqual(
            [project.genome_version, project.description, project.workspace_namespace, project.workspace_name],
            ['38', 'A test project', TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        mock_add_service_account.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)
        mock_has_service_account.assert_not_called()
        mock_time.sleep.assert_not_called()
        mock_file_exist.assert_called_with('gs://test_bucket/test_path.vcf', user=self.manager_user)
        mock_file_iter.assert_called_with('gs://test_bucket/test_path.vcf', byte_range=None)
        mock_tempfile.assert_called_with(mode='wb', delete=False)
        mock_tempfile.return_value.__enter__.return_value.write.assert_called_with(b's\nNA19675\nNA19678\nHG00735')
        mock_mv_file.assert_called_with(
            TEMP_PATH, 'gs://seqr-datasets/v02/GRCh38/AnVIL_WES/{guid}/base/{guid}_ids.txt'.format(guid=project.guid),
            user=self.manager_user
        )
        slack_message = """
        *test_user_manager@test.com* requested to load WES data (GRCh38) from AnVIL workspace *my-seqr-billing/anvil-no-project-workspace1* at 
        gs://test_bucket/test_path.vcf to seqr project <http://testserver/project/{guid}/project_page|*anvil-no-project-workspace1*> (guid: {guid})  
  
        The sample IDs to load have been uploaded to gs://seqr-datasets/v02/GRCh38/AnVIL_WES/{guid}/base/{guid}_ids.txt.  
  
        DAG for the loading pipeline:
        ```{{
    "active_projects": [
        "{guid}"
    ],
    "vcf_path": "gs://test_bucket/test_path.vcf",
    "project_path": "gs://seqr-datasets/v02/GRCh38/AnVIL_WES/{guid}/v1",
    "projects_to_run": [
        "{guid}"
    ]
}}```
        """.format(guid=project.guid)
        mock_slack.assert_called_with(SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, slack_message)

        # Test project exist
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Project "{name}" for workspace "{namespace}/{name}" exists.'
                         .format(namespace=TEST_WORKSPACE_NAMESPACE, name=TEST_NO_PROJECT_WORKSPACE_NAME))

        # Test saving ID file exception
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME2])
        mock_mv_file.side_effect = Exception('Something wrong while moving the ID file.')
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        mock_api_logger.error.assert_called_with('Uploading sample IDs to Google Storage failed. Errors: Something wrong while moving the ID file.',
                      self.manager_user, detail=['HG00735', 'NA19675', 'NA19678'])

        # Test logged in locally
        remove_token(self.manager_user)  # The user will look like having logged in locally after the access token is removed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/api/create_project_from_workspace/submit/my-seqr-billing/anvil-no-project-workspace2')


class NoGoogleAnvilWorkspaceAPITest(AuthenticationTestCase):
    fixtures = ['users']

    def test_anvil_workspace_page(self):
        url = reverse(anvil_workspace_page, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME])
        self.check_require_login(url, login_redirect_url='/login/google-oauth2', policy_redirect_url='/accept_policies')

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/workspace/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de')

    def test_create_project_from_workspace(self):
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME])
        self.check_require_login(url, login_redirect_url='/login/google-oauth2')

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/api/create_project_from_workspace/submit/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de')
