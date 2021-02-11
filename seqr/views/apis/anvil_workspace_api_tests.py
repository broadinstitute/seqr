import json
import mock

from django.urls.base import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from seqr.models import Project
from seqr.views.apis.anvil_workspace_api import anvil_workspace_page, create_project_from_workspace
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase

WORKSPACE_NAMESPACE = 'my-seqr-billing'
EXIST_WORKSPACE_NAME = 'anvil-project 1000 Genomes Demo'
WORKSPACE_NAME = 'anvil project name'
NEW_WORKSPACE_NAME = 'anvil new project'

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
        }

@mock.patch('seqr.utils.middleware.logger')
@mock.patch('seqr.views.utils.permissions_utils.user_get_workspace_access_level')
class AnvilWorkspaceAPITest(AnvilAuthenticationTestCase):
    fixtures = ['users', 'social_auth', '1kg_project']

    def test_anvil_workspace_page(self, mock_get_access_level, mock_logger):
        # Requesting to load data for a non-existing project
        url = reverse(anvil_workspace_page, args=[WORKSPACE_NAMESPACE, WORKSPACE_NAME])
        self.check_collaborator_login(url)

        mock_get_access_level.return_value = {"pending": False, "canShare": True, "accessLevel": "WRITER"}
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/create_project_from_workspace/my-seqr-billing/anvil%20project%20name')

        # Requesting to load data for an existing project
        url = reverse(anvil_workspace_page, args=[WORKSPACE_NAMESPACE, EXIST_WORKSPACE_NAME])

        mock_get_access_level.return_value = {"pending": False, "canShare": True, "accessLevel": "WRITER"}
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/project/R0003_test/project_page')

        # Test lack of permissions
        mock_logger.reset_mock()
        mock_get_access_level.return_value = {"pending": False, "canShare": False, "accessLevel": "WRITER"}
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        mock_logger.warning.assert_called_with('', extra=mock.ANY)

    @mock.patch('seqr.views.apis.anvil_workspace_api.load_uploaded_file')
    @mock.patch('seqr.views.apis.anvil_workspace_api.add_service_account')
    @mock.patch('seqr.utils.communication_utils.EmailMessage')
    @mock.patch('seqr.views.apis.anvil_workspace_api.logger')
    def test_create_project_from_workspace(self, mock_local_logger, mock_email, mock_add_service_account,
                                           mock_load_file, mock_get_access_level, mock_logger):
        # Requesting to load data for a non-existing project
        url = reverse(create_project_from_workspace, args=[WORKSPACE_NAMESPACE, WORKSPACE_NAME])
        self.check_collaborator_login(url)

        # Test lack of permissions
        mock_logger.reset_mock()
        mock_get_access_level.return_value = {"pending": False, "canShare": True, "accessLevel": "READER"}
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        mock_logger.warning.assert_called_with('test_user_collaborator does not have sufficient permissions for workspace my-seqr-billing/anvil project name',
            extra=mock.ANY)

        # Test missing required fields in the request body
        mock_get_access_level.return_value = {"pending": False, "canShare": True, "accessLevel": "OWNER"}
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Field(s) "genomeVersion, uploadedFileId" are required')

        data = {
            'genomeVersion': '38',
            'uploadedFileId': 'test_temp_file_id',
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

        # Test valid operation
        mock_add_service_account.return_value = True
        mock_load_file.return_value = LOAD_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(workspace_namespace=WORKSPACE_NAMESPACE, workspace_name=WORKSPACE_NAME)
        response_json = response.json()
        self.assertEqual(project.guid, response_json['projectGuid'])
        self.assertListEqual(
            [project.genome_version, project.description, project.workspace_namespace, project.workspace_name],
            ['38', 'A test project', WORKSPACE_NAMESPACE, WORKSPACE_NAME])
        mock_add_service_account.assert_called_with(mock.ANY, WORKSPACE_NAMESPACE, WORKSPACE_NAME)
        mock_email.assert_called_with(
            subject='AnVIL data loading request',
            body="""
    Data from AnVIL workspace "{namespace}/{name}" needs to be loaded to seqr project <a href="http://testserver/project/{guid}/project_page">{name}</a> (guid: {guid})

    The sample IDs to load are attached.    
    """.format(namespace=WORKSPACE_NAMESPACE, name=WORKSPACE_NAME, guid=project.guid),
            to=['test_superuser@test.com', 'test_data_manager@test.com'],
            attachments=[('{}_sample_ids.tsv'.format(project.guid), 'Individual ID\nNA19675\nNA19678\nHG00735')]
        )

        # Test project exist
        url = reverse(create_project_from_workspace, args=[WORKSPACE_NAMESPACE, WORKSPACE_NAME])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Project "anvil project name" for workspace "{}/{}" exists.'
                         .format(WORKSPACE_NAMESPACE, WORKSPACE_NAME))

        # Test sending email exception
        url = reverse(create_project_from_workspace, args=[WORKSPACE_NAMESPACE, NEW_WORKSPACE_NAME])
        mock_email.side_effect = Exception('Something wrong while sending email.')
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        mock_local_logger.error.assert_called_with('Exception while sending email to user test_user_collaborator. Something wrong while sending email.')
