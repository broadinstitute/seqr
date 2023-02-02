from copy import deepcopy
from datetime import datetime
import json
import mock
from django.urls.base import reverse
import responses

from seqr.models import Project
from seqr.views.apis.anvil_workspace_api import anvil_workspace_page, create_project_from_workspace, \
    validate_anvil_vcf, grant_workspace_access, add_workspace_data, get_anvil_vcf_list
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, AuthenticationTestCase, TEST_WORKSPACE_NAMESPACE,\
    TEST_WORKSPACE_NAME, TEST_WORKSPACE_NAME1, TEST_NO_PROJECT_WORKSPACE_NAME, TEST_NO_PROJECT_WORKSPACE_NAME2
from seqr.views.utils.terra_api_utils import remove_token, TerraAPIException, TerraRefreshTokenFailedException
from settings import SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

LOAD_SAMPLE_DATA = [
    ["Family ID", "Individual ID", "Previous Individual ID", "Paternal ID", "Maternal ID", "Sex", "Affected Status",
     "Notes", "familyNotes"],
    ["1", "NA19675", "NA19675_1", "NA19678", "", "Female", "Affected", "A affected individual, test1-zsf", ""],
    ["1", "NA19678", "", "", "", "Male", "Unaffected", "a individual note", ""],
    ["21", "HG00735", "", "", "", "", "", "", "a new family"]]

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
        "project_path": "gs://seqr-datasets/v02/GRCh38/AnVIL_WES/{guid}/v20210301".format(guid=TEST_GUID),
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

PROJECT1_SAMPLES = ['HG00735', 'NA19675', 'NA19678', 'NA20870', 'HG00732', 'NA19675_1', 'NA20874', 'HG00733', 'HG00731']
PROJECT2_SAMPLES = ['HG00735', 'NA19675', 'NA19678', 'NA20885']

REQUEST_BODY_ADD_DATA = deepcopy(REQUEST_BODY)
REQUEST_BODY_ADD_DATA['vcfSamples'] = PROJECT1_SAMPLES

REQUEST_BODY_ADD_DATA2 = deepcopy(REQUEST_BODY)
REQUEST_BODY_ADD_DATA2['vcfSamples'] = PROJECT2_SAMPLES

PROJECT1_GUID = 'R0001_1kg'
PROJECT2_GUID = 'R0003_test'
ADD_DATA_UPDATED_ANVIL_VARIABLES = {
    "key": "AnVIL_WES",
    "value": json.dumps({
        "active_projects": [PROJECT1_GUID],
        "vcf_path": "gs://test_bucket/test_path.vcf",
        "project_path": "gs://seqr-datasets/v02/GRCh37/AnVIL_WES/{guid}/v20210301".format(guid=PROJECT1_GUID),
        "projects_to_run": [PROJECT1_GUID] })
}
ADD_DATA_UPDATE_DAG_TASKS_RESP = {
            "tasks": [
                {
                    "task_id": "create_dataproc_cluster",
                },
                {
                    "task_id": f"pyspark_compute_project_{PROJECT1_GUID}",
                },
                {
                    "task_id": "pyspark_compute_variants_AnVIL_WES",
                },
                {
                    "task_id": f"pyspark_export_project_{PROJECT1_GUID}",
                },
                {
                    "task_id": "scale_dataproc_cluster",
                },
                {
                    "task_id": f"skip_compute_project_subset_{PROJECT1_GUID}",
                }
                ],
            "total_entries": 6
        }

BASIC_META = [
    '##fileformat=VCFv4.3\n'
    '##source=myImputationProgramV3.1\n',
    '##FILTER=<ID=q10,Description="Quality below 10">',
    '##FILTER=<ID=s50,Description="Less than 50% of samples have data">',
]

BAD_INFO_META = [
    '##INFO=<ID=AA,Number=1,Type=String,Description="Ancestral Allele">',
    '##INFO=<ID=DB,Number=0,Type=Flag,Description="dbSNP membership, build 129">',
    '##INFO=<ID=H2,Number=0,Type=Flag,Description="HapMap2 membership">',
    '##INFO=<ID=AC,Number=A,Type=Integer,Description="Allele count in genotypes, for each ALT allele, in the same order as listed">\n',
    '##INFO=<ID=AF,Number=A,Type=Integer,Description="Allele Frequency, for each ALT allele, in the same order as listed">\n',
]

INFO_META = [
    '##INFO=<ID=AA,Number=1,Type=String,Description="Ancestral Allele">',
    '##INFO=<ID=AC,Number=A,Type=Integer,Description="Allele count in genotypes, for each ALT allele, in the same order as listed">\n',
    '##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency, for each ALT allele, in the same order as listed">\n',
    '##INFO=<ID=AN,Number=1,Type=Integer,Description="Total number of alleles in called genotypes">\n',
]

BAD_FORMAT_META = [
    '##FORMAT=<ID=AD,Number=.,Type=Integer,Description="Allelic depths for the ref and alt alleles in the order listed">\n',
    '##FORMAT=<ID=DP,Number=1,Type=String,Description="Approximate read depth (reads with MQ=255 or with bad mates are filtered)">\n',
]

FORMAT_META = [
    '##FORMAT=<ID=AD,Number=.,Type=Integer,Description="Allelic depths for the ref and alt alleles in the order listed">\n',
    '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Approximate read depth (reads with MQ=255 or with bad mates are filtered)">\n',
    '##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype Quality">\n',
    '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n',
]

BAD_HEADER_LINE = ['#CHROM\tID\tREF\tALT\tQUAL\n']
NO_SAMPLE_HEADER_LINE = ['#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\n']
HEADER_LINE = ['#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG00735\tNA19675\tNA19678\n']

DATA_LINES = [
    'chr1\t10333\t.\tCT\tC\t1895\tPASS\tAC=5;AF=0.045;AN=112;DP=22546\tGT:AD:DP:GQ\t./.:63,0:63\t./.:44,0:44\t./.:44,0:44\n'
]


@mock.patch('seqr.views.utils.permissions_utils.logger')
class AnvilWorkspaceAPITest(AnvilAuthenticationTestCase):
    fixtures = ['users', 'social_auth', '1kg_project']

    @mock.patch('seqr.views.apis.anvil_workspace_api.logger')
    def test_anvil_workspace_page(self, mock_api_logger, mock_logger):
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
        self.mock_get_ws_access_level.assert_called_with(
            self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME, meta_fields=['workspace.authorizationDomain']
        )
        mock_api_logger.warning.assert_not_called()

        # Test workspace with authorization domains
        auth_domains_url = reverse(anvil_workspace_page, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME2])
        response = self.client.post(auth_domains_url)
        self.assertEqual(response.status_code, 403)
        self.mock_get_ws_access_level.assert_called_with(
            self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME2,
            meta_fields=['workspace.authorizationDomain']
        )
        mock_api_logger.warning.assert_called_with(
            'Unable to load data from anvil workspace with authorization domains "my-seqr-billing/anvil-no-project-workspace2"',
            self.manager_user)

        # Test error handling when token refresh fails
        self.mock_get_ws_access_level.side_effect = TerraRefreshTokenFailedException('Failed to refresh token')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            '/login/google-oauth2?next=/workspace/{}/{}'.format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME)
        )
        self.mock_get_ws_access_level.assert_called_with(
            self.manager_user, TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME, meta_fields=['workspace.authorizationDomain']
        )

        # Requesting to load data for an existing project
        self.mock_get_ws_access_level.reset_mock()
        url = reverse(anvil_workspace_page, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/project/R0001_1kg/project_page')
        self.mock_get_ws_access_level.assert_not_called()

    @mock.patch('seqr.views.apis.anvil_workspace_api.logger')
    @mock.patch('seqr.views.apis.anvil_workspace_api.time')
    @mock.patch('seqr.views.apis.anvil_workspace_api.has_service_account_access')
    @mock.patch('seqr.views.apis.anvil_workspace_api.add_service_account')
    def test_grant_workspace_access(self, mock_add_service_account, mock_has_service_account, mock_time, mock_logger, mock_utils_logger):

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
        mock_logger.info.assert_called_with(
            f'Added service account for {TEST_WORKSPACE_NAMESPACE}/{TEST_NO_PROJECT_WORKSPACE_NAME}, waiting for access to grant',
            self.manager_user,
        )

        # Test logged in locally
        remove_token(
            self.manager_user)  # The user will look like having logged in locally after the access token is removed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         '/login/google-oauth2?next=/api/create_project_from_workspace/my-seqr-billing/anvil-no-project-workspace1/grant_access')

    @mock.patch('seqr.views.apis.anvil_workspace_api.does_file_exist')
    @mock.patch('seqr.utils.vcf_utils.file_iter')
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

        # test no header line
        mock_file_exist.return_value = True
        mock_file_iter.return_value = BASIC_META + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'No header found in the VCF file.'
        ])
        mock_file_iter.assert_called_with('gs://test_bucket/test_path.vcf.gz', byte_range=(0, 65536))
        mock_file_exist.assert_called_with('gs://test_bucket/test_path.vcf.gz', user=self.manager_user)

        # test header errors
        mock_file_iter.return_value = BASIC_META + BAD_INFO_META + BAD_FORMAT_META + BAD_HEADER_LINE + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Missing required VCF header field(s) POS, FILTER, INFO, FORMAT.'
        ])

        # test no samples
        mock_file_iter.return_value = BASIC_META + NO_SAMPLE_HEADER_LINE + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['No samples found in the provided VCF.'])

        # test meta info errors
        mock_file_iter.return_value = BASIC_META + BAD_INFO_META + BAD_FORMAT_META + HEADER_LINE + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Missing required INFO field(s) AN',
            'Incorrect meta Type for INFO.AF - expected "Float", got "Integer"',
            'Missing required FORMAT field(s) GQ, GT',
            'Incorrect meta Type for FORMAT.DP - expected "Integer", got "String"'
        ])

        # Test valid operation
        mock_file_exist.return_value = True
        mock_file_iter.return_value = BASIC_META + INFO_META + FORMAT_META + HEADER_LINE + DATA_LINES
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

    @mock.patch('seqr.utils.file_utils.logger')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_get_anvil_vcf_list(self, mock_subprocess, mock_file_logger, mock_utils_logger):
        # Requesting to load data from a workspace without an existing project
        url = reverse(get_anvil_vcf_list, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME1])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')
        mock_utils_logger.warning.assert_called_with('User does not have sufficient permissions for workspace {}/{}'
                                                     .format(TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME1),
                                                     self.collaborator_user)

        # Test empty bucket
        mock_subprocess.return_value.wait.return_value = 0
        mock_subprocess.return_value.stdout = b''
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'dataPathList': []})
        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://test_bucket', stdout=-1, stderr=-2, shell=True),
            mock.call().wait(),
        ])

        # Test valid operation
        mock_subprocess.return_value.stdout = [
            b'Warning: some packages are out of date',
            b'gs://test_bucket/test.vcf', b'gs://test_bucket/data/test.vcf.gz', b'gs://test_bucket/test.tsv',
        ]
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'dataPathList': ['/test.vcf', '/data/test.vcf.gz']})
        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://test_bucket', stdout=-1, stderr=-2, shell=True),
            mock.call().wait(),
            mock.call('gsutil ls gs://test_bucket/**', stdout=-1, stderr=-2, shell=True),
            mock.call().wait(),
        ])
        mock_file_logger.info.assert_has_calls([
            mock.call('==> gsutil ls gs://test_bucket', self.manager_user),
            mock.call('==> gsutil ls gs://test_bucket/**', self.manager_user),
        ])


class LoadAnvilDataAPITest(AnvilAuthenticationTestCase):
    fixtures = ['users', 'social_auth', '1kg_project']

    def setUp(self):
        # Set up api responses
        responses.add(responses.POST, f'{MOCK_AIRTABLE_URL}/appUelDNM3BnWaR7M/AnVIL%20Seqr%20Loading%20Requests%20Tracking', status=400)
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
        # get task id again if the response of the previous request didn't include the updated guid
        responses.add(responses.GET,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/tasks'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json=UPDATE_DAG_TASKS_RESP,
                      status=200)
        # get task id again if the response of the previous request didn't include the updated guid
        responses.add(responses.GET,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/tasks'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json=ADD_DATA_UPDATE_DAG_TASKS_RESP,
                      status=200)
        # trigger dag
        responses.add(responses.POST,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json={},
                      status=200)

        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.id_token.fetch_id_token', lambda *args: MOCK_TOKEN)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_API_KEY', MOCK_AIRTABLE_KEY)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_URL', MOCK_AIRTABLE_URL)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.AIRFLOW_WEBSERVER_URL', MOCK_AIRFLOW_URL)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.BASE_URL', 'http://testserver/')
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('seqr.views.utils.permissions_utils.logger')
        self.mock_utils_logger = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.airtable_utils.logger')
        self.mock_airtable_logger = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.load_uploaded_file')
        self.mock_load_file = patcher.start()
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.safe_post_to_slack')
        self.mock_slack = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.mv_file_to_gs')
        self.mock_mv_file = patcher.start()
        self.mock_mv_file.return_value = True
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.tempfile.NamedTemporaryFile')
        self.mock_tempfile = patcher.start()
        self.mock_tempfile.return_value.__enter__.return_value.name = TEMP_PATH
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.logger')
        self.mock_api_logger = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.datetime')
        self.mock_datetime = patcher.start()
        self.mock_datetime.now.side_effect = lambda: datetime(2021, 3, 1, 0, 0, 0)
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.send_html_email')
        self.mock_send_email = patcher.start()
        self.addCleanup(patcher.stop)

        super(LoadAnvilDataAPITest, self).setUp()

    @mock.patch('seqr.models.Project._compute_guid', lambda project: f'P_{project.name}')
    @responses.activate
    def test_create_project_from_workspace(self):
        # Requesting to load data from a workspace without an existing project
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')
        self.mock_utils_logger.warning.assert_called_with('User does not have sufficient permissions for workspace {}/{}'
                                               .format(TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME),
                                               self.collaborator_user)

        self._test_errors(url, ['genomeVersion', 'uploadedFileId', 'fullDataPath', 'vcfSamples', 'sampleType'],
                          TEST_NO_PROJECT_WORKSPACE_NAME)

        # Test valid operation
        responses.calls.reset()
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(workspace_namespace=TEST_WORKSPACE_NAMESPACE, workspace_name=TEST_NO_PROJECT_WORKSPACE_NAME)
        response_json = response.json()
        self.assertEqual(project.guid, response_json['projectGuid'])
        self.assertListEqual(
            [project.genome_version, project.description, project.workspace_namespace, project.workspace_name],
            ['38', 'A test project', TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])

        self.assertListEqual(
            [project.mme_contact_institution, project.mme_primary_data_owner, project.mme_contact_url],
            ['Broad Center for Mendelian Genomics', 'Test Manager User', 'mailto:test_user_manager@test.com'])

        self._assert_valid_operation(project, test_add_data=False)

        # Test project exist
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Project "{name}" for workspace "{namespace}/{name}" exists.'
                         .format(namespace=TEST_WORKSPACE_NAMESPACE, name=TEST_NO_PROJECT_WORKSPACE_NAME))

        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME2])
        self._test_mv_file_and_triggering_dag_exception(
            url, {'workspace_namespace': TEST_WORKSPACE_NAMESPACE, 'workspace_name': TEST_NO_PROJECT_WORKSPACE_NAME2},
            ['HG00735', 'NA19675', 'NA19678'], 'GRCh38', REQUEST_BODY)

    @responses.activate
    def test_add_workspace_data(self):
        # Test insufficient Anvil workspace permission
        url = reverse(add_workspace_data, args=[PROJECT2_GUID])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')
        self.mock_utils_logger.warning.assert_called_with(
            'User does not have sufficient permissions for workspace my-seqr-billing/anvil-project 1000 Genomes Demo',
            self.collaborator_user)

        # Test requesting to load data from a workspace without an existing project
        url = reverse(add_workspace_data, args=['no_PROJECT1_GUID'])
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'Project matching query does not exist.')

        url = reverse(add_workspace_data, args=[PROJECT1_GUID])
        self._test_errors(url, ['uploadedFileId', 'fullDataPath', 'vcfSamples'], TEST_WORKSPACE_NAME)

        # Test missing loaded samples
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'In order to add new data to this project, new samples must be joint called in a single VCF with all previously'
            ' loaded samples. The following samples were previously loaded in this project but are missing from the VCF:'
            ' HG00731, HG00732, HG00733, NA19675_1, NA20870, NA20874')

        # Test a valid operation
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_ADD_DATA))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'familiesByGuid', 'familyNotesByGuid', 'individualsByGuid'})
        self.assertSetEqual(set(response_json['individualsByGuid'].keys()), {'I0000019_hg00735', 'I000001_na19675', 'I000002_na19678'})
        self.assertSetEqual(set(response_json['familiesByGuid'].keys()), {'F000001_1', 'F000015_21'})
        self.assertEqual(list(response_json['familyNotesByGuid'].keys()), ['FAN000004_21_c_a_new_family'])

        self._assert_valid_operation(Project.objects.get(guid=PROJECT1_GUID))

        url = reverse(add_workspace_data, args=[PROJECT2_GUID])
        self._test_mv_file_and_triggering_dag_exception(url, {'guid': PROJECT2_GUID}, PROJECT2_SAMPLES, 'GRCh37', REQUEST_BODY_ADD_DATA2)

    def _test_errors(self, url, fields, workspace_name):
        # Test missing required fields in the request body
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        field_str = ', '.join(fields)
        self.assertEqual(response.reason_phrase, f'Field(s) "{field_str}" are required')
        self.mock_get_ws_access_level.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE, workspace_name)

        # test missing columns
        self.mock_load_file.return_value = [['family', 'individual'], ['1', '2']]
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertListEqual(response_json['errors'], [
            'Error while converting uploaded pedigree file rows to json: Sex, Affected not specified in row #1'])

        # test sample data error
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA + BAD_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertListEqual(response_json['errors'], [
            'NA19679 is the mother of NA19674 but is not included. Make sure to create an additional record with NA19679 as the Individual ID',
        ])

        # test missing samples
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA_EXTRA_SAMPLE
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['errors'],
                         ['The following samples are included in the pedigree file but are missing from the VCF: NA19679'])

    def _assert_valid_operation(self, project, test_add_data=True):
        if test_add_data:
            updated_anvil_variables = ADD_DATA_UPDATED_ANVIL_VARIABLES
            genome_version = 'GRCh37'
            temp_file_data = b's\nHG00731\nHG00732\nHG00733\nHG00735\nNA19675\nNA19675_1\nNA19678\nNA19678\nNA20870\nNA20874'
        else:
            updated_anvil_variables = UPDATED_ANVIL_VARIABLES
            genome_version = 'GRCh38'
            temp_file_data = b's\nHG00735\nNA19675\nNA19678'

        self.mock_api_logger.error.assert_not_called()

        self.mock_tempfile.assert_called_with(mode='wb', delete=False)
        self.mock_tempfile.return_value.__enter__.return_value.write.assert_called_with(temp_file_data)
        self.mock_mv_file.assert_called_with(
            TEMP_PATH, f'gs://seqr-datasets/v02/{genome_version}/AnVIL_WES/{project.guid}/base/{project.guid}_ids.txt',
            user=self.manager_user
        )

        # Test triggering anvil dags
        self.assertEqual(len(responses.calls), 7 if test_add_data else 6)
        # check dag running state
        self.assertEqual(responses.calls[0].request.url, '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[0].request.method, "GET")
        self.assertEqual(responses.calls[0].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))
        self.assertEqual(responses.calls[0].response.json(), DAG_RUNS)

        # update variables
        self.assertEqual(responses.calls[1].request.url, '{}/api/v1/variables/AnVIL_WES'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[1].request.method, "PATCH")
        self.assertDictEqual(json.loads(responses.calls[1].request.body), updated_anvil_variables)
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

        call_cnt = 5 if test_add_data else 4
        if test_add_data:
            self.assertEqual(responses.calls[4].request.url, '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/tasks'.format(MOCK_AIRFLOW_URL))
            self.assertEqual(responses.calls[4].request.method, 'GET')
            self.assertEqual(responses.calls[4].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))
            self.assertEqual(responses.calls[4].response.json(), ADD_DATA_UPDATE_DAG_TASKS_RESP)

        # trigger dag
        self.assertEqual(responses.calls[call_cnt].request.url, '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[call_cnt].request.method, 'POST')
        self.assertDictEqual(json.loads(responses.calls[call_cnt].request.body), {})
        self.assertEqual(responses.calls[call_cnt].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))

        # create airtable record
        self.assertDictEqual(json.loads(responses.calls[call_cnt+1].request.body), {'records': [{'fields': {
            'Requester Name': 'Test Manager User',
            'Requester Email': 'test_user_manager@test.com',
            'AnVIL Project URL': f'http://testserver/project/{project.guid}/project_page',
            'Initial Request Date': '2021-03-01',
            'Number of Samples': 10 if test_add_data else 3,
            'Status': 'Loading',
        }}]})
        self.assertEqual(responses.calls[call_cnt+1].request.headers['Authorization'], 'Bearer {}'.format(MOCK_AIRTABLE_KEY))

        slack_message = """
        *test_user_manager@test.com* requested to load 3 WES samples ({version}) from AnVIL workspace *my-seqr-billing/{workspace_name}* at 
        gs://test_bucket/test_path.vcf to seqr project <http://testserver/project/{guid}/project_page|*{project_name}*> (guid: {guid})  
  
        The sample IDs to load have been uploaded to gs://seqr-datasets/v02/{version}/AnVIL_WES/{guid}/base/{guid}_ids.txt.  
  
        DAG seqr_vcf_to_es_AnVIL_WES_v0.0.1 is triggered with following:
        ```{{
    "active_projects": [
        "{guid}"
    ],
    "vcf_path": "gs://test_bucket/test_path.vcf",
    "project_path": "gs://seqr-datasets/v02/{version}/AnVIL_WES/{guid}/v20210301",
    "projects_to_run": [
        "{guid}"
    ]
}}```
        """.format(guid=project.guid, version=genome_version, workspace_name=project.workspace_name,
                   project_name=project.name)
        self.mock_slack.assert_called_with(SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, slack_message)
        self.mock_send_email.assert_not_called()

    def _test_mv_file_and_triggering_dag_exception(self, url, workspace, samples, genome_version, request_body):
        # Test saving ID file exception
        responses.calls.reset()
        self.mock_mv_file.side_effect = Exception('Something wrong while moving the ID file.')
        # Test triggering dag exception
        responses.replace(responses.GET,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL),
                      json=DAG_RUNS_RUNNING)

        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(**workspace)

        self.mock_api_logger.error.assert_called_with(
            'Uploading sample IDs to Google Storage failed. Errors: Something wrong while moving the ID file.',
            self.manager_user, detail=samples)
        self.mock_api_logger.warning.assert_called_with(
            'seqr_vcf_to_es_AnVIL_WES_v0.0.1 is running and cannot be triggered again.', self.manager_user)
        self.mock_airtable_logger.error.assert_called_with(
            f'Airtable create "AnVIL Seqr Loading Requests Tracking" error: 400 Client Error: Bad Request for url: '
            f'{MOCK_AIRTABLE_URL}/appUelDNM3BnWaR7M/AnVIL%20Seqr%20Loading%20Requests%20Tracking', self.manager_user)

        slack_message_on_failure = """
        ERROR triggering AnVIL loading for project {guid}: seqr_vcf_to_es_AnVIL_WES_v0.0.1 is running and cannot be triggered again. 
        
        DAG seqr_vcf_to_es_AnVIL_WES_v0.0.1 should be triggered with following: 
        ```{{
    "active_projects": [
        "{guid}"
    ],
    "vcf_path": "gs://test_bucket/test_path.vcf",
    "project_path": "gs://seqr-datasets/v02/{version}/AnVIL_WES/{guid}/v20210301",
    "projects_to_run": [
        "{guid}"
    ]
}}```
        """.format(
            guid=project.guid,
            version=genome_version,
        )
        self.mock_slack.assert_any_call(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, slack_message_on_failure)
        self.mock_send_email.assert_not_called()
        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(responses.calls[0].request.url, '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/dagRuns'.format(MOCK_AIRFLOW_URL))
        self.assertEqual(responses.calls[0].request.method, "GET")
        self.assertEqual(responses.calls[0].request.headers['Authorization'], 'Bearer {}'.format(MOCK_TOKEN))
        self.assertEqual(responses.calls[0].response.json(), DAG_RUNS_RUNNING)

        # Airtable record created with correct status
        self.assertDictEqual(json.loads(responses.calls[1].request.body), {'records': [{'fields': {
            'Requester Name': 'Test Manager User',
            'Requester Email': 'test_user_manager@test.com',
            'AnVIL Project URL': f'http://testserver/project/{project.guid}/project_page',
            'Initial Request Date': '2021-03-01',
            'Number of Samples': len(samples),
            'Status': 'Loading Requested',
        }}]})

    @mock.patch('seqr.views.apis.anvil_workspace_api.ANVIL_LOADING_DELAY_EMAIL_START_DATE', '2021-06-01')
    @responses.activate
    def test_create_project_from_workspace_loading_delay_email(self):
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')

        # make sure the task id including the newly created project to avoid infinitely pulling the tasks
        responses.add(responses.GET,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/tasks'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json={"tasks": [
                            {"task_id": "pyspark_compute_project_R0006_anvil_no_project_workspace"},
                            {"task_id": "pyspark_compute_project_R0007_anvil_no_project_workspace"},
                            {"task_id": "pyspark_compute_project_R0008_anvil_no_project_workspace"}],
                            "total_entries": 2},
                      status=200)
        self._test_not_yet_email_date(url, REQUEST_BODY)

        # Remove created project to allow future requests
        project = Project.objects.get(
            workspace_namespace=TEST_WORKSPACE_NAMESPACE, workspace_name=TEST_NO_PROJECT_WORKSPACE_NAME)
        project.workspace_name = None
        project.save()

        self._test_after_email_date(url, REQUEST_BODY)

    @mock.patch('seqr.views.apis.anvil_workspace_api.ANVIL_LOADING_DELAY_EMAIL_START_DATE', '2021-06-01')
    @responses.activate
    def test_add_workspace_data_loading_delay_email(self):
        url = reverse(add_workspace_data, args=[PROJECT1_GUID])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')

        # make sure the task id including the newly created project to avoid infinitely pulling the tasks
        responses.add(responses.GET,
                      '{}/api/v1/dags/seqr_vcf_to_es_AnVIL_WES_v0.0.1/tasks'.format(MOCK_AIRFLOW_URL),
                      headers={'Authorization': 'Bearer {}'.format(MOCK_TOKEN)},
                      json={"tasks": [
                          {"task_id": "pyspark_compute_project_R0003_test"},
                          {"task_id": "pyspark_compute_project_R0004_test"}],
                          "total_entries": 2},
                      status=200)
        self._test_not_yet_email_date(url, REQUEST_BODY_ADD_DATA)

        url = reverse(add_workspace_data, args=[PROJECT2_GUID])
        self._test_after_email_date(url, REQUEST_BODY_ADD_DATA2)

    def _test_not_yet_email_date(self, url, request_body):
        self.mock_send_email.side_effect = ValueError('Unable to send email')
        self.mock_datetime.strptime.side_effect = datetime.strptime

        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        self.mock_send_email.assert_not_called()

    def _test_after_email_date(self, url, request_body):
        self.mock_datetime.now.side_effect = lambda: datetime(2021, 9, 1, 0, 0, 0)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        self.mock_send_email.assert_called_with("""Hi Test Manager User,
            We have received your request to load data to seqr from AnVIL. Currently, the Broad Institute is holding an 
            internal retreat or closed for the winter break so we are unable to load data until mid-January 
            2022. We appreciate your understanding and support of our research team taking 
            some well-deserved time off and hope you also have a nice break.
            - The seqr team
            """, subject='Delay in loading AnVIL in seqr', to=['test_user_manager@test.com'])
        self.mock_api_logger.error.assert_called_with(
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

    def test_add_workspace_data(self):
        url = reverse(add_workspace_data, args=[PROJECT1_GUID])
        self.check_require_login(url, login_redirect_url='/login/google-oauth2')

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/google-oauth2?next=/api/project/R0001_1kg/add_workspace_data')
