from copy import deepcopy
from datetime import datetime
import json
import mock
from django.urls.base import reverse
import responses

from seqr.models import Project
from seqr.views.apis.anvil_workspace_api import anvil_workspace_page, create_project_from_workspace, \
    validate_anvil_vcf, grant_workspace_access
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, AuthenticationTestCase, TEST_WORKSPACE_NAMESPACE,\
    TEST_WORKSPACE_NAME, TEST_NO_PROJECT_WORKSPACE_NAME, TEST_NO_PROJECT_WORKSPACE_NAME2
from seqr.views.utils.terra_api_utils import remove_token, TerraAPIException, TerraRefreshTokenFailedException
from settings import SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

LOAD_SAMPLE_DATA = [
    ["Family ID", "Individual ID", "Previous Individual ID", "Paternal ID", "Maternal ID", "Sex", "Affected Status",
     "Notes", "familyNotes"],
    ["1", "NA19675", "NA19675_1", "NA19678", "", "Female", "Affected", "A affected individual, test1-zsf", ""],
    ["1", "NA19678", "", "", "", "Male", "Unaffected", "a individual note", ""],
    ["21", "HG00735", "", "", "", "Female", "Unaffected", "", "a new family"]]

BAD_SAMPLE_DATA = [["1", "NA19674", "NA19674_1", "NA19678", "NA19679", "Female", "Affected", "A affected individual, test1-zsf", ""]]

LOAD_SAMPLE_DATA_EXTRA_SAMPLE = LOAD_SAMPLE_DATA + [["1", "NA19679", "", "", "", "Male", "Affected", "", ""]]

FILE_DATA = [
    '##fileformat=VCFv4.2\n',
    '#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	NA19675	NA19678	HG00735\n',
    'chr1	1000	test\n',
]

GRANT_ACCESS_BODY = {'agreeSeqrAccess': True}

VALIDATE_VCF_BODY = {
    'genomeVersion': '38',
    'sampleType': 'WES',
    'dataPath': 'test_path.vcf',
}
REQUEST_BODY_NO_SLASH_DATA_PATH = deepcopy(VALIDATE_VCF_BODY)
REQUEST_BODY_NO_SLASH_DATA_PATH['dataPath'] = 'test_no_slash_path.vcf.bgz'
REQUEST_BODY_BAD_DATA_PATH = deepcopy(VALIDATE_VCF_BODY)
REQUEST_BODY_BAD_DATA_PATH['dataPath'] = 'test_path.vcf.tar'
REQUEST_BODY_GZ_DATA_PATH = deepcopy(VALIDATE_VCF_BODY)
REQUEST_BODY_GZ_DATA_PATH['dataPath'] = '/test_path.vcf.gz'

VALIDATE_VFC_RESPONSE = {
    'vcfSamples': ['HG00735', 'NA19675', 'NA19678'],
    'fullDataPath': 'gs://test_bucket/test_path.vcf',
}

REQUEST_BODY = {
    'uploadedFileId': 'test_temp_file_id',
    'description': 'A test project',
}
REQUEST_BODY.update(GRANT_ACCESS_BODY)
REQUEST_BODY.update(VALIDATE_VCF_BODY)
REQUEST_BODY.update(VALIDATE_VFC_RESPONSE)

TEMP_PATH = '/temp_path/temp_filename'

TEST_GUID=f'P_{TEST_NO_PROJECT_WORKSPACE_NAME}'
MOCK_TOKEN = 'mock_openid_bearer' # nosec
MOCK_AIRFLOW_URL = 'http://testairflowserver'
MOCK_AIRTABLE_URL = 'http://testairtable'
MOCK_AIRTABLE_KEY = 'mock_key' # nosec

DAG_RUNS = {
    'dag_runs': [
        {'conf': {},
         'dag_id': 'seqr_vcf_to_es_AnVIL_WGS_v0.0.1',
         'dag_run_id': 'manual__2022-04-28T11:51:22.735124+00:00',
         'end_date': None, 'execution_date': '2022-04-28T11:51:22.735124+00:00',
         'external_trigger': True, 'start_date': '2022-04-28T11:51:25.626176+00:00',
         'state': 'success'}
    ]
}

DAG_RUNS_RUNNING = {
    'dag_runs': [
        {'conf': {},
         'dag_id': 'seqr_vcf_to_es_AnVIL_WGS_v0.0.1',
         'dag_run_id': 'manual__2022-04-28T11:51:22.735124+00:00',
         'end_date': None, 'execution_date': '2022-04-28T11:51:22.735124+00:00',
         'external_trigger': True, 'start_date': '2022-04-28T11:51:25.626176+00:00',
         'state': 'running'}
    ]
}

UPDATED_ANVIL_VARIABLES = {
    "key": "AnVIL_WES",
    "value": json.dumps({
        "active_projects": [TEST_GUID],
        "vcf_path": "gs://test_bucket/test_path.vcf",
        "project_path": "gs://seqr-datasets/v02/GRCh38/AnVIL_WES/{guid}/v1".format(guid=TEST_GUID),
        "projects_to_run": [TEST_GUID] })
}

DAG_TASKS_RESP = {
    "tasks": [
        {
            "task_id": "create_dataproc_cluster",
        },
        {
            "task_id": "pyspark_compute_project_R0006_test",
        },
        {
            "task_id": "pyspark_compute_variants_AnVIL_WES",
        },
        {
            "task_id": "pyspark_export_project_R0006_test",
        },
        {
            "task_id": "scale_dataproc_cluster",
        },
        {
            "task_id": "skip_compute_project_subset_R0006_test",
        }
        ],
    "total_entries": 6
}
UPDATE_DAG_TASKS_RESP = {
            "tasks": [
                {
                    "task_id": "create_dataproc_cluster",
                },
                {
                    "task_id": f"pyspark_compute_project_{TEST_GUID}",
                },
                {
                    "task_id": "pyspark_compute_variants_AnVIL_WES",
                },
                {
                    "task_id": f"pyspark_export_project_{TEST_GUID}",
                },
                {
                    "task_id": "scale_dataproc_cluster",
                },
                {
                    "task_id": f"skip_compute_project_subset_{TEST_GUID}",
                }
                ],
            "total_entries": 6
        }

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

    @mock.patch('seqr.views.apis.anvil_workspace_api.time')
    @mock.patch('seqr.views.apis.anvil_workspace_api.has_service_account_access')
    @mock.patch('seqr.views.apis.anvil_workspace_api.add_service_account')
    def test_grant_workspace_access(self, mock_add_service_account, mock_has_service_account, mock_time,  mock_utils_logger):

        # Requesting to load data from a workspace without an existing project
        url = reverse(grant_workspace_access,
                      args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')
        mock_utils_logger.warning.assert_called_with('User does not have sufficient permissions for workspace {}/{}'
                                                     .format(TEST_WORKSPACE_NAMESPACE,
                                                             TEST_NO_PROJECT_WORKSPACE_NAME),
                                                     self.collaborator_user)
        self.mock_get_ws_access_level.assert_called_with(self.collaborator_user, TEST_WORKSPACE_NAMESPACE,
                                                         TEST_NO_PROJECT_WORKSPACE_NAME)

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase,
                         'Must agree to grant seqr access to the data in the associated workspace.')

        # Test adding service account exception
        mock_add_service_account.side_effect = TerraAPIException(
            'Failed to grant seqr service account access to the workspace {}/{}'
            .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME), 400)
        response = self.client.post(url, content_type='application/json', data=json.dumps(GRANT_ACCESS_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'],
                         'Failed to grant seqr service account access to the workspace {}/{}'
                         .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME))

        # Test adding service account never processes
        mock_add_service_account.reset_mock(side_effect=True)
        mock_add_service_account.return_value = True
        mock_has_service_account.return_value = False
        response = self.client.post(url, content_type='application/json', data=json.dumps(GRANT_ACCESS_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Failed to grant seqr service account access to the workspace')
        mock_has_service_account.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE,
                                                    TEST_NO_PROJECT_WORKSPACE_NAME)
        self.assertEqual(mock_has_service_account.call_count, 2)
        self.assertEqual(mock_time.sleep.call_count, 2)

        # Test valid operation
        mock_time.reset_mock()
        mock_has_service_account.reset_mock()
        mock_add_service_account.return_value = False
        response = self.client.post(url, content_type='application/json', data=json.dumps(GRANT_ACCESS_BODY))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})
        mock_add_service_account.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE,
                                                    TEST_NO_PROJECT_WORKSPACE_NAME)
        mock_has_service_account.assert_not_called()
        mock_time.sleep.assert_not_called()

        # Test logged in locally
        remove_token(
            self.manager_user)  # The user will look like having logged in locally after the access token is removed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         '/login/google-oauth2?next=/api/create_project_from_workspace/my-seqr-billing/anvil-no-project-workspace1/grant_access')

    @mock.patch('seqr.views.apis.anvil_workspace_api.does_file_exist')
    @mock.patch('seqr.views.apis.anvil_workspace_api.file_iter')
    def test_validate_anvil_vcf(self, mock_file_iter, mock_file_exist, mock_utils_logger):
        # Requesting to load data from a workspace without an existing project
        url = reverse(validate_anvil_vcf,
                      args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')
        mock_utils_logger.warning.assert_called_with('User does not have sufficient permissions for workspace {}/{}'
                                                     .format(TEST_WORKSPACE_NAMESPACE,
                                                             TEST_NO_PROJECT_WORKSPACE_NAME),
                                                     self.collaborator_user)

        # Test missing required fields in the request body
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'dataPath is required')
        self.mock_get_ws_access_level.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE,
                                                         TEST_NO_PROJECT_WORKSPACE_NAME,
                                                         meta_fields=['workspace.bucketName'])

        # Test bad data path
        mock_file_exist.return_value = False
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_NO_SLASH_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Data file or path test_no_slash_path.vcf.bgz is not found.')
        mock_file_exist.assert_called_with('gs://test_bucket/test_no_slash_path.vcf.bgz', user=self.manager_user)

        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_BAD_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'],
                         'Invalid VCF file format - file path must end with .vcf or .vcf.gz or .vcf.bgz')

        mock_file_exist.return_value = True
        mock_file_iter.return_value = ['##fileformat=VCFv4.2\n',
                                       '#CHROM	POS	ID	REF	ALT	QUAL']  # incomplete header line
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'],
                         'No samples found in the provided VCF. This may be due to a malformed file')
        mock_file_iter.assert_called_with('gs://test_bucket/test_path.vcf.gz', byte_range=(0, 65536))
        mock_file_exist.assert_called_with('gs://test_bucket/test_path.vcf.gz', user=self.manager_user)

        # Test valid operation
        mock_file_exist.return_value = True
        mock_file_iter.return_value = FILE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(VALIDATE_VCF_BODY))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), VALIDATE_VFC_RESPONSE)
        mock_file_exist.assert_called_with('gs://test_bucket/test_path.vcf', user=self.manager_user)
        mock_file_iter.assert_called_with('gs://test_bucket/test_path.vcf', byte_range=None)

        # Test logged in locally
        remove_token(
            self.manager_user)  # The user will look like having logged in locally after the access token is removed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         '/login/google-oauth2?next=/api/create_project_from_workspace/my-seqr-billing/anvil-no-project-workspace1/validate_vcf')

    @mock.patch('seqr.models.Project._compute_guid', lambda project: f'P_{project.name}')
    @mock.patch('seqr.views.apis.anvil_workspace_api.id_token.fetch_id_token', lambda *args: MOCK_TOKEN)
    @mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_API_KEY', MOCK_AIRTABLE_KEY)
    @mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_URL', MOCK_AIRTABLE_URL)
    @mock.patch('seqr.views.apis.anvil_workspace_api.AIRFLOW_WEBSERVER_URL', MOCK_AIRFLOW_URL)
    @mock.patch('seqr.views.apis.anvil_workspace_api.BASE_URL', 'http://testserver/')
    @mock.patch('seqr.views.apis.anvil_workspace_api.ANVIL_LOADING_DELAY_EMAIL', None)
    @mock.patch('seqr.views.utils.airtable_utils.logger')
    @mock.patch('seqr.views.apis.anvil_workspace_api.datetime')
    @mock.patch('seqr.views.apis.anvil_workspace_api.logger')
    @mock.patch('seqr.views.apis.anvil_workspace_api.load_uploaded_file')
    @mock.patch('seqr.views.apis.anvil_workspace_api.send_html_email')
    @mock.patch('seqr.views.apis.anvil_workspace_api.safe_post_to_slack')
    @mock.patch('seqr.views.apis.anvil_workspace_api.mv_file_to_gs')
    @mock.patch('seqr.views.apis.anvil_workspace_api.tempfile.NamedTemporaryFile')
    @responses.activate
    def test_create_project_from_workspace(self, mock_tempfile, mock_mv_file, mock_slack,
                                           mock_send_email, mock_load_file, mock_api_logger, mock_datetime,
                                           mock_airtable_logger, mock_utils_logger):
        # Set up api responses
        airtable_tracking_url = f'{MOCK_AIRTABLE_URL}/appUelDNM3BnWaR7M/AnVIL%20Seqr%20Loading%20Requests%20Tracking'
        responses.add(responses.POST, airtable_tracking_url, status=400)
        # check dag running state
        responses.add(responses.GET,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json=DAG_RUNS,
                      status=200)
        # update variables
        responses.add(responses.PATCH,
                      '{}/api/v1/variables/AnVIL_WES'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json={'key': 'AnVIL_WES', 'value': 'updated variables'},
                      status=200)
        # get task id
        responses.add(responses.GET,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/tasks'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json=DAG_TASKS_RESP,
                      status=200)
        # get task id again if the response of the previous requset didn't include the updated guid
        responses.add(responses.GET,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/tasks'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json=UPDATE_DAG_TASKS_RESP,
                      status=200)
        # trigger dag
        responses.add(responses.POST,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json={},
                      status=200)

        # Requesting to load data from a workspace without an existing project
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')
        mock_utils_logger.warning.assert_called_with('User does not have sufficient permissions for workspace {}/{}'
                                               .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME),
                                               self.collaborator_user)

        # Test missing required fields in the request body
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Field(s) "genomeVersion, uploadedFileId, fullDataPath, vcfSamples, sampleType" are required')
        self.mock_get_ws_access_level.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)

        # Test parsing sample data error
        mock_load_file.return_value = LOAD_SAMPLE_DATA + BAD_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertListEqual(response_json['errors'], ['NA19679 is the mother of NA19674 but doesn\'t have a separate record in the table'])

        # Test missing samples
        mock_load_file.return_value = LOAD_SAMPLE_DATA_EXTRA_SAMPLE
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'],
                         'The following samples are included in the pedigree file but are missing from the VCF: NA19679')

        # Test valid operation
        responses.calls.reset()
        mock_load_file.return_value = LOAD_SAMPLE_DATA
        mock_tempfile.return_value.__enter__.return_value.name = TEMP_PATH
        mock_datetime.now.side_effect = lambda: datetime(2021, 3, 1, 0, 0, 0)
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(workspace_namespace=TEST_WORKSPACE_NAMESPACE, workspace_name=TEST_NO_PROJECT_WORKSPACE_NAME)
        response_json = response.json()
        self.assertEqual(project.guid, response_json['projectGuid'])
        self.assertListEqual(
            [project.genome_version, project.description, project.workspace_namespace, project.workspace_name],
            ['38', 'A test project', TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        mock_api_logger.error.assert_not_called()

        self.assertListEqual(
            [project.mme_contact_institution, project.mme_primary_data_owner, project.mme_contact_url],
            ['Broad Center for Mendelian Genomics', 'Test Manager User', 'mailto:test_user_manager@test.com'])

        mock_tempfile.assert_called_with(mode='wb', delete=False)
        mock_tempfile.return_value.__enter__.return_value.write.assert_called_with(b's\nNA19675\nNA19678\nHG00735')
        mock_mv_file.assert_called_with(
            TEMP_PATH, 'gs://seqr-datasets/v02/GRCh38/AnVIL_WES/{guid}/base/{guid}_ids.txt'.format(guid=project.guid),
            user=self.manager_user
        )

        # Test triggering anvil dags
        self.assertEqual(len(responses.calls), 6)
        # check dag running state
        self.assertEqual(responses.calls[0].request.url, '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[0].request.method, "GET")
        self.assertEqual(responses.calls[0].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))
        self.assertEqual(responses.calls[0].response.json(), DAG_RUNS)


        # update variables
        self.assertEqual(responses.calls[1].request.url, '{}/api/v1/variables/AnVIL_WES'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[1].request.method, "PATCH")
        self.assertDictEqual(json.loads(responses.calls[1].request.body), UPDATED_ANVIL_VARIABLES)
        self.assertEqual(responses.calls[1].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))

        # get task id
        self.assertEqual(responses.calls[2].request.url, '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/tasks'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[2].request.method, 'GET')
        self.assertEqual(responses.calls[2].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))
        self.assertEqual(responses.calls[2].response.json(), DAG_TASKS_RESP)

        self.assertEqual(responses.calls[3].request.url, '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/tasks'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[3].request.method, 'GET')
        self.assertEqual(responses.calls[3].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))
        self.assertEqual(responses.calls[3].response.json(), UPDATE_DAG_TASKS_RESP)

        # trigger dag
        self.assertEqual(responses.calls[4].request.url, '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[4].request.method, 'POST')
        self.assertDictEqual(json.loads(responses.calls[4].request.body), {})
        self.assertEqual(responses.calls[4].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))

        # create airtable record
        self.assertDictEqual(json.loads(responses.calls[5].request.body), {'records': [{'fields': {
            'Requester Name': 'Test Manager User',
            'Requester Email': 'test_user_manager@test.com',
            'AnVIL Project URL': f'http://testserver/project/{project.guid}/project_page',
            'Initial Request Date': '2021-03-01',
            'Number of Samples': 3,
            'Status': 'Loading',
        }}]})
        self.assertEqual(responses.calls[5].request.headers['Authorization'], 'Bearer {}'.format(MOCK_AIRTABLE_KEY))

        slack_message = """
        *test_user_manager@test.com* requested to load WES data (GRCh38) from AnVIL workspace *my-seqr-billing/anvil-no-project-workspace1* at 
        gs://test_bucket/test_path.vcf to seqr project <http://testserver/project/{guid}/project_page|*anvil-no-project-workspace1*> (guid: {guid})  
  
        The sample IDs to load have been uploaded to gs://seqr-datasets/v02/GRCh38/AnVIL_WES/{guid}/base/{guid}_ids.txt.  
  
        DAG seqr_vcf_to_es_AnVIL_WES_v0.0.1 is triggered with following:
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
        mock_send_email.assert_not_called()

        # Test project exist
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Project "{name}" for workspace "{namespace}/{name}" exists.'
                         .format(namespace=TEST_WORKSPACE_NAMESPACE, name=TEST_NO_PROJECT_WORKSPACE_NAME))

        # Test saving ID file exception
        responses.calls.reset()
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME2])
        mock_mv_file.side_effect = Exception('Something wrong while moving the ID file.')
        # Test triggering dag exception
        responses.replace(responses.GET,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL),
                      json=DAG_RUNS_RUNNING)

        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        project2 = Project.objects.get(workspace_namespace=TEST_WORKSPACE_NAMESPACE, workspace_name=TEST_NO_PROJECT_WORKSPACE_NAME2)

        mock_api_logger.error.assert_called_with(
            'Uploading sample IDs to Google Storage failed. Errors: Something wrong while moving the ID file.',
            self.manager_user, detail=['HG00735', 'NA19675', 'NA19678'])
        mock_api_logger.warning.assert_called_with(
            'seqr_vcf_to_es_AnVIL_WES_v0.0.1 is running and cannot be triggered again.', self.manager_user)
        mock_airtable_logger.error.assert_called_with(
            f'Airtable create "AnVIL Seqr Loading Requests Tracking" error: 400 Client Error: Bad Request for url: {airtable_tracking_url}', self.manager_user)

        slack_message_on_failure = """
        ERROR triggering AnVIL loading for project {guid}: seqr_vcf_to_es_AnVIL_WES_v0.0.1 is running and cannot be triggered again. 
        
        DAG seqr_vcf_to_es_AnVIL_WES_v0.0.1 should be triggered with following: 
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
        """.format(
            guid=project2.guid,
            airflow_url = MOCK_AIRFLOW_URL
        )
        mock_slack.assert_any_call(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, slack_message_on_failure)
        mock_send_email.assert_not_called()
        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(responses.calls[0].request.url, '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[0].request.method, "GET")
        self.assertEqual(responses.calls[0].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))
        self.assertEqual(responses.calls[0].response.json(), DAG_RUNS_RUNNING)

        # Airtable record created with correct status
        self.assertDictEqual(json.loads(responses.calls[1].request.body), {'records': [{'fields': {
            'Requester Name': 'Test Manager User',
            'Requester Email': 'test_user_manager@test.com',
            'AnVIL Project URL': f'http://testserver/project/{project2.guid}/project_page',
            'Initial Request Date': '2021-03-01',
            'Number of Samples': 3,
            'Status': 'Loading Requested',
        }}]})

        # Test logged in locally
        remove_token(self.manager_user)  # The user will look like having logged in locally after the access token is removed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/api/create_project_from_workspace/my-seqr-billing/anvil-no-project-workspace2/submit')

    @mock.patch('seqr.views.apis.anvil_workspace_api.ANVIL_LOADING_DELAY_EMAIL', 'We are unable to load your data at this time.')
    @mock.patch('seqr.views.apis.anvil_workspace_api.ANVIL_LOADING_EMAIL_DATE', '2021-06-01')
    @mock.patch('seqr.views.apis.anvil_workspace_api.mv_file_to_gs', lambda *args, **kwargs: True)
    @mock.patch('seqr.views.apis.anvil_workspace_api.load_uploaded_file', lambda *args, **kwargs: LOAD_SAMPLE_DATA)
    @mock.patch('seqr.views.apis.anvil_workspace_api.logger')
    @mock.patch('seqr.views.apis.anvil_workspace_api.datetime')
    @mock.patch('seqr.views.apis.anvil_workspace_api.send_html_email')
    @responses.activate
    def test_create_project_from_workspace_loading_delay_email(
            self, mock_send_email, mock_datetime, mock_api_logger, mock_utils_logger):
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')

        # Test not yet anvil email date
        mock_send_email.side_effect = ValueError('Unable to send email')
        mock_datetime.strptime.side_effect = datetime.strptime
        mock_datetime.now.side_effect = lambda: datetime(2021, 3, 1, 0, 0, 0)

        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        mock_send_email.assert_not_called()

        # Remove created project to allow future requests
        project = Project.objects.get(
            workspace_namespace=TEST_WORKSPACE_NAMESPACE, workspace_name=TEST_NO_PROJECT_WORKSPACE_NAME)
        project.workspace_name = None
        project.save()

        # Test after anvil email date
        mock_datetime.now.side_effect = lambda: datetime(2021, 9, 1, 0, 0, 0)
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        mock_send_email.assert_called_with("""Hi Test Manager User,
            We are unable to load your data at this time.
            - The seqr team
            """, subject='Delay in loading AnVIL in seqr', to=['test_user_manager@test.com'])
        mock_api_logger.error.assert_called_with(
            'AnVIL loading delay email error: Unable to send email', self.manager_user)


class NoGoogleAnvilWorkspaceAPITest(AuthenticationTestCase):
    fixtures = ['users']

    def test_anvil_workspace_page(self):
        url = reverse(anvil_workspace_page, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME])
        self.check_require_login(url, login_redirect_url='/login/google-oauth2', policy_redirect_url='/accept_policies')

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/workspace/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de')

    def _test_api_access(self, test_func, path):
        url = reverse(test_func, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME])
        self.check_require_login(url, login_redirect_url='/login/google-oauth2')

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/login/google-oauth2?next=/api/create_project_from_workspace/my-seqr-billing/anvil-1kg%2520project%2520n%25C3%25A5me%2520with%2520uni%25C3%25A7%25C3%25B8de/{path}')

    def test_grant_workspace_access(self):
        self._test_api_access(grant_workspace_access, 'grant_access')

    def test_validate_anvil_vcf(self):
        self._test_api_access(validate_anvil_vcf, 'validate_vcf')

    def test_create_project_from_workspace(self):
        self._test_api_access(create_project_from_workspace, 'submit')
