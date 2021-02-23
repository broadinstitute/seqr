import json
import mock

from django.contrib.auth.models import User
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.anvil_workspace_api import anvil_workspace_page, create_project_from_workspace
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, AuthenticationTestCase, TEST_WORKSPACE_NAMESPACE,\
    TEST_WORKSPACE_NAME, TEST_NO_PROJECT_WORKSPACE_NAME, TEST_NO_PROJECT_WORKSPACE_NAME2
from seqr.views.utils.terra_api_utils import remove_token, TerraAPIException

LOAD_SAMPLE_DATA = [
    ["Family ID", "Individual ID", "Previous Individual ID", "Paternal ID", "Maternal ID", "Sex", "Affected Status",
     "Notes", "familyNotes"],
    ["1", "NA19675", "NA19675_1", "NA19678", "", "Female", "Affected", "A affected individual, test1-zsf", ""],
    ["1", "NA19678", "", "", "", "Male", "Unaffected", "a individual note", ""],
    ["21", "HG00735", "", "", "", "Female", "Unaffected", "", "a new family"]]

BAD_SAMPLE_DATA = [["1", "NA19674", "NA19674_1", "NA19678", "NA19679", "Female", "Affected", "A affected individual, test1-zsf", ""]]

REQUEST_BODY = {
            'genomeVersion': '38',
            'uploadedFileId': 'test_temp_file_id',
            'description': 'A test project',
            'agreeSeqrAccess': True,
            'dataPath': '/test_path'
        }


@mock.patch('seqr.views.utils.permissions_utils.logger')
class AnvilWorkspaceAPITest(AnvilAuthenticationTestCase):
    fixtures = ['users', 'social_auth', '1kg_project']

    def test_anvil_workspace_page(self, mock_logger):
        # Requesting to load data from a workspace without an existing project
        url = reverse(anvil_workspace_page, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])

        # Test user doesn't login
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/workspace/{}/{}'
                         .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME))

        # Test the user needs sufficient workspace permissions
        self.check_manager_login(url)
        mock_logger.warning.assert_called_with('test_user_collaborator does not have sufficient permissions for workspace {}/{}'
                                               .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME))

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/create_project_from_workspace/{}/{}'.format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME))
        user = User.objects.get(username='test_user_manager')
        self.mock_get_ws_access_level.assert_called_with(user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)

        # Requesting to load data for an existing project
        url = reverse(anvil_workspace_page, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME])
        self.check_manager_login(url)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/project/R0001_1kg/project_page')
        self.mock_get_ws_access_level.assert_called_with(user, TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME)

        # Test login locally
        remove_token(user)  # The user will be same as logging in locally after the access token is removed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/workspace/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de')

    @mock.patch('seqr.utils.communication_utils.BASE_URL', 'http://testserver')
    @mock.patch('seqr.views.apis.anvil_workspace_api.logger')
    @mock.patch('seqr.views.apis.anvil_workspace_api.load_uploaded_file')
    @mock.patch('seqr.views.apis.anvil_workspace_api.add_service_account')
    @mock.patch('seqr.utils.communication_utils.EmailMessage')
    @mock.patch('seqr.views.apis.anvil_workspace_api.does_file_exist')
    def test_create_project_from_workspace(self, mock_file_exist, mock_email, mock_add_service_account,
                                           mock_load_file, mock_api_logger, mock_utils_logger):
        # Requesting to load data from a workspace without an existing project
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])

        # Test user doesn't login
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/api/create_project_from_workspace/submit/{}/{}'
                         .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME))

        # Test the user needs sufficient workspace permissions
        self.check_manager_login(url)
        mock_utils_logger.warning.assert_called_with('test_user_collaborator does not have sufficient permissions for workspace {}/{}'
                                               .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME))

        # Test missing required fields in the request body
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Field(s) "genomeVersion, uploadedFileId, dataPath" are required')
        user = User.objects.get(username='test_user_manager')
        self.mock_get_ws_access_level.assert_called_with(user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME, meta_fields=['workspace.bucketName'])

        data = {
            'genomeVersion': '38',
            'uploadedFileId': 'test_temp_file_id',
            'dataPath': '/test_path',
        }
        response = self.client.post(url, content_type='application/json', data=json.dumps(data))
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

        # Test bad data path
        mock_add_service_account.reset_mock(side_effect=True)
        mock_file_exist.return_value = False
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Data file or path /test_path is not found.')
        mock_file_exist.assert_called_with('gs://test_bucket/test_path')

        # Test valid operation
        mock_file_exist.return_value = True
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(workspace_namespace=TEST_WORKSPACE_NAMESPACE, workspace_name=TEST_NO_PROJECT_WORKSPACE_NAME)
        response_json = response.json()
        self.assertEqual(project.guid, response_json['projectGuid'])
        self.assertListEqual(
            [project.genome_version, project.description, project.workspace_namespace, project.workspace_name],
            ['38', 'A test project', TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        mock_add_service_account.assert_called_with(user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)
        mock_email.assert_called_with(
            subject='AnVIL data loading request',
            body="""
    Data from AnVIL workspace "{namespace}/{name}" at "gs://test_bucket/test_path" needs to be loaded to seqr project
    <a href="http://testserver/project/{guid}/project_page">{name}</a> (guid: {guid})

    The sample IDs to load are attached.    
    """.format(namespace=TEST_WORKSPACE_NAMESPACE, name=TEST_NO_PROJECT_WORKSPACE_NAME, guid=project.guid),
            to=['test_superuser@test.com', 'test_data_manager@test.com'],
            attachments=[('{}_sample_ids.tsv'.format(project.guid), 'NA19675\nNA19678\nHG00735')]
        )

        # Test project exist
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Project "{name}" for workspace "{namespace}/{name}" exists.'
                         .format(namespace=TEST_WORKSPACE_NAMESPACE, name=TEST_NO_PROJECT_WORKSPACE_NAME))

        # Test sending email exception
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME2])
        mock_email.side_effect = Exception('Something wrong while sending email.')
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        mock_api_logger.error.assert_called_with('Exception while sending email to user test_user_manager. Something wrong while sending email.')

        # Test logged in locally
        remove_token(user)  # The user will look like having logged in locally after the access token is removed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/api/create_project_from_workspace/submit/my-seqr-billing/anvil-no-project-workspace2')


class NoGoogleAnvilWorkspaceAPITest(AuthenticationTestCase):
    fixtures = ['users']

    def test_anvil_workspace_page(self):
        url = reverse(anvil_workspace_page, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/workspace/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de')

        self.login_base_user()
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/workspace/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de')

    def test_create_project_from_workspace(self):
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/api/create_project_from_workspace/submit/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de')

        self.login_base_user()
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/api/create_project_from_workspace/submit/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de')
