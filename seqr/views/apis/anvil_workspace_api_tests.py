from copy import deepcopy
from datetime import datetime
import json
import mock
from django.urls.base import reverse
import responses

from seqr.models import Project, Family, Individual
from seqr.views.apis.anvil_workspace_api import anvil_workspace_page, create_project_from_workspace, \
    validate_anvil_vcf, grant_workspace_access, add_workspace_data, get_anvil_vcf_list, get_anvil_igv_options
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, AuthenticationTestCase, AirflowTestCase, AirtableTest, \
    TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME, TEST_WORKSPACE_NAME1, TEST_NO_PROJECT_WORKSPACE_NAME, TEST_NO_PROJECT_WORKSPACE_NAME2
from seqr.views.utils.terra_api_utils import remove_token, TerraAPIException, TerraRefreshTokenFailedException
from settings import SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

LOAD_SAMPLE_DATA = [
    ["Family ID", "Individual ID", "Previous Individual ID", "Paternal ID", "Maternal ID", "Sex", "Affected Status",
     "HPO Terms", "Notes", "familyNotes"],
    ["1", " NA19675_1 ", "NA19675_1 ", "", "NA19679 ", "Female", "Affected", "HP:0012469 (Infantile spasms); HP:0011675 (Arrhythmia)", "A affected individual, test1-zsf", ""],
    ["1", "NA19679", "", "", "", "Female", "Unaffected", "", "a individual note", ""],
    ["21", " HG00735", "", "", "", "Unknown", "Affected", "HP:0001508,HP:0001508", "", "a new family"]]

BAD_SAMPLE_DATA = [["1", "NA19674", "NA19674_1", "NA19678", "NA19679", "Female", "Affected", "", "A affected individual, test1-zsf", ""],
                   ["1", "NA19681", "", "", "", "Male", "Affected", "HP:0100258", "", ""]]
INVALID_ADDED_SAMPLE_DATA = [['22', 'HG00731', 'HG00731', '', '', 'Female', 'Affected', 'HP:0011675', '', '']]

MISSING_REQUIRED_SAMPLE_DATA = [["21", "HG00736", "", "", "", "", "", "", "", ""]]

LOAD_SAMPLE_DATA_EXTRA_SAMPLE = LOAD_SAMPLE_DATA + [["1", "NA19678", "", "", "", "Male", "Affected", "HP:0011675", "", ""]]

LOAD_SAMPLE_DATA_NO_AFFECTED = LOAD_SAMPLE_DATA + [["22", "HG00736", "", "", "", "Unknown", "Unknown", "", "", ""]]

FILE_DATA = [
    '##fileformat=VCFv4.2\n',
    '#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	NA19675_1	NA19679	HG00735\n',
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
REQUEST_BODY_SHARDED_DATA_PATH = deepcopy(VALIDATE_VCF_BODY)
REQUEST_BODY_SHARDED_DATA_PATH['dataPath'] = '/test_path-*.vcf.gz'

VALIDATE_VFC_RESPONSE = {
    'vcfSamples': ['HG00735', 'NA19675_1', 'NA19679'],
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

MOCK_AIRTABLE_URL = 'http://testairtable'

PROJECT1_SAMPLES = ['HG00735', 'NA19678', 'NA19679', 'NA20870', 'HG00732', 'NA19675_1', 'NA20874', 'HG00733', 'HG00731']
PROJECT2_SAMPLES = ['NA20885', 'NA19675_1', 'NA19679', 'HG00735']
PROJECT2_SAMPLE_DATA = [
    {'Project_GUID': 'R0003_test', 'Family_GUID': 'F000016_1', 'Family_ID': '1', 'Individual_ID': 'NA19675_1', 'Paternal_ID': None, 'Maternal_ID': 'NA19679', 'Sex': 'F'},
    {'Project_GUID': 'R0003_test', 'Family_GUID': 'F000016_1', 'Family_ID': '1', 'Individual_ID': 'NA19679', 'Paternal_ID': None, 'Maternal_ID': None, 'Sex': 'F'},
    {'Project_GUID': 'R0003_test', 'Family_GUID': 'F000017_21', 'Family_ID': '21', 'Individual_ID': 'HG00735', 'Paternal_ID': None, 'Maternal_ID': None, 'Sex': 'U'},
]

NEW_PROJECT_SAMPLE_DATA = [
    {'Project_GUID': 'P_anvil-no-project-workspace2', 'Family_GUID': 'F_1_workspace2', 'Family_ID': '1', 'Individual_ID': 'NA19675_1', 'Paternal_ID': None, 'Maternal_ID': 'NA19679', 'Sex': 'F'},
    {'Project_GUID': 'P_anvil-no-project-workspace2', 'Family_GUID': 'F_1_workspace2', 'Family_ID': '1', 'Individual_ID': 'NA19679', 'Paternal_ID': None, 'Maternal_ID': None, 'Sex': 'F'},
    {'Project_GUID': 'P_anvil-no-project-workspace2', 'Family_GUID': 'F_21_workspace2', 'Family_ID': '21', 'Individual_ID': 'HG00735', 'Paternal_ID': None, 'Maternal_ID': None, 'Sex': 'U'},
]

REQUEST_BODY_ADD_DATA = deepcopy(REQUEST_BODY)
REQUEST_BODY_ADD_DATA['vcfSamples'] = PROJECT1_SAMPLES

REQUEST_BODY_ADD_DATA2 = deepcopy(REQUEST_BODY)
REQUEST_BODY_ADD_DATA2['vcfSamples'] = PROJECT2_SAMPLES

PROJECT1_GUID = 'R0001_1kg'
PROJECT2_GUID = 'R0003_test'

BASIC_META = [
    b'##fileformat=VCFv4.3\n',
    b'##source=myImputationProgramV3.1\n',
    b'##FILTER=<ID=q10,Description="Quality below 10">',
    b'##FILTER=<ID=s50,Description="Less than 50% of samples have data">',
]

BAD_INFO_META = [
    b'##INFO=<ID=AA,Number=1,Type=String,Description="Ancestral Allele">',
    b'##INFO=<ID=DB,Number=0,Type=Flag,Description="dbSNP membership, build 129">',
    b'##INFO=<ID=H2,Number=0,Type=Flag,Description="HapMap2 membership">',
    b'##INFO=<ID=AC,Number=A,Type=Integer,Description="Allele count in genotypes, for each ALT allele, in the same order as listed">\n',
    b'##INFO=<ID=AF,Number=A,Type=Integer,Description="Allele Frequency, for each ALT allele, in the same order as listed">\n',
]

INFO_META = [
    b'##INFO=<ID=AA,Number=1,Type=String,Description="Ancestral Allele">',
    b'##INFO=<ID=AC,Number=A,Type=Integer,Description="Allele count in genotypes, for each ALT allele, in the same order as listed">\n',
    b'##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency, for each ALT allele, in the same order as listed">\n',
    b'##INFO=<ID=AN,Number=1,Type=Integer,Description="Total number of alleles in called genotypes">\n',
]

BAD_FORMAT_META = [
    b'##FORMAT=<ID=AD,Number=.,Type=Integer,Description="Allelic depths for the ref and alt alleles in the order listed">\n',
    b'##FORMAT=<ID=GQ,Number=1,Type=String,Description="Genotype Quality">\n',
    b'##reference=file:///references/grch37/reference.bin\n',
]

FORMAT_META = [
    b'##FORMAT=<ID=AD,Number=.,Type=Integer,Description="Allelic depths for the ref and alt alleles in the order listed">\n',
    b'##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Approximate read depth (reads with MQ=255 or with bad mates are filtered)">\n',
    b'##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype Quality">\n',
    b'##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n',
]

REFERENCE_META = [
    b'##reference=file:///gpfs/internal/sweng/production/Resources/GRCh38_1000genomes/GRCh38_full_analysis_set_plus_decoy_hla.fa\n'
]

BAD_HEADER_LINE = [b'#CHROM\tID\tREF\tALT\tQUAL\n']
NO_SAMPLE_HEADER_LINE = [b'#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\n']
HEADER_LINE = [b'#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG00735\tNA19675_1\tNA19679\n']

DATA_LINES = [
    b'chr1\t10333\t.\tCT\tC\t1895\tPASS\tAC=5;AF=0.045;AN=112;DP=22546\tGT:AD:DP:GQ\t./.:63,0:63\t./.:44,0:44\t./.:44,0:44\n'
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

    @mock.patch('seqr.utils.file_utils.logger')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_validate_anvil_vcf(self, mock_subprocess, mock_file_logger, mock_utils_logger):
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
        self.assertEqual(response.reason_phrase, 'Field(s) "genomeVersion, dataPath" are required')
        self.mock_get_ws_access_level.assert_called_with(self.manager_user, TEST_WORKSPACE_NAMESPACE,
                                                         TEST_NO_PROJECT_WORKSPACE_NAME,
                                                         meta_fields=['workspace.bucketName'])

        # Test pending loading project
        response = self.client.post(url, content_type='application/json', data=json.dumps({**VALIDATE_VCF_BODY, 'genomeVersion': '37'}))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Project "Empty Project" is awaiting loading. Please wait for loading to complete before requesting additional data loading'
        ])

        # Test bad data path
        mock_subprocess.return_value.wait.return_value = -1
        mock_subprocess.return_value.stdout = [b'File not found']
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Data file or path /test_path.vcf.gz is not found.'])
        mock_subprocess.assert_called_with('gsutil ls gs://test_bucket/test_path.vcf.gz', stdout=-1, stderr=-2, shell=True)  # nosec
        mock_file_logger.info.assert_has_calls([
            mock.call('==> gsutil ls gs://test_bucket/test_path.vcf.gz', self.manager_user),
            mock.call('File not found', self.manager_user),
        ])

        # Test bad sharded data path
        mock_file_logger.reset_mock()
        mock_subprocess.return_value.communicate.return_value = b'', b'File not found'
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_SHARDED_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Data file or path /test_path-*.vcf.gz is not found.'])
        mock_subprocess.assert_called_with('gsutil ls gs://test_bucket/test_path-*.vcf.gz', stdout=-1, stderr=-1, shell=True)  # nosec
        mock_file_logger.info.assert_has_calls([
            mock.call('==> gsutil ls gs://test_bucket/test_path-*.vcf.gz', self.manager_user),
            mock.call('File not found', self.manager_user),
        ])

        # Test empty sharded data path
        mock_file_logger.reset_mock()
        mock_subprocess.return_value.communicate.return_value = b'\n', b''
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_SHARDED_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Data file or path /test_path-*.vcf.gz is not found.'])
        mock_subprocess.assert_called_with('gsutil ls gs://test_bucket/test_path-*.vcf.gz', stdout=-1, stderr=-1, shell=True)  # nosec
        mock_file_logger.info.assert_has_calls([
            mock.call('==> gsutil ls gs://test_bucket/test_path-*.vcf.gz', self.manager_user),
        ])

        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_BAD_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'],
                         ['Invalid VCF file format - file path must end with .vcf or .vcf.gz or .vcf.bgz'])

        # test no header line
        mock_subprocess.reset_mock()
        mock_subprocess.return_value.wait.return_value = 0
        mock_subprocess.return_value.stdout = BASIC_META + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['No header found in the VCF file.'])
        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://test_bucket/test_path.vcf.gz', stdout=-1, stderr=-2, shell=True),  # nosec
            mock.call().wait(),
            mock.call('gsutil cat -r 0-65536 gs://test_bucket/test_path.vcf.gz | gunzip -c -q - ',
                      stdout=-1, stderr=-2, shell=True),  # nosec
        ])
        mock_file_logger.info.assert_has_calls([
            mock.call('==> gsutil ls gs://test_bucket/test_path.vcf.gz', self.manager_user),
            mock.call('==> gsutil cat -r 0-65536 gs://test_bucket/test_path.vcf.gz | gunzip -c -q - ', None),
        ])

        # test header errors
        mock_subprocess.return_value.stdout = BASIC_META + BAD_INFO_META + BAD_FORMAT_META + BAD_HEADER_LINE + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Missing required VCF header field(s) POS, FILTER, INFO, FORMAT.'
        ])

        # test no samples
        mock_subprocess.return_value.stdout = BASIC_META + NO_SAMPLE_HEADER_LINE + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['No samples found in the provided VCF.'])

        # test meta info errors
        mock_subprocess.return_value.stdout = BASIC_META + BAD_INFO_META + BAD_FORMAT_META + HEADER_LINE + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_GZ_DATA_PATH))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Missing required FORMAT field(s) GT',
            'Incorrect meta Type for FORMAT.GQ - expected "Integer", got "String"',
            'Mismatched genome version - VCF metadata indicates GRCh37, GRCH38 provided',
        ])

        # Test valid operations
        mock_subprocess.reset_mock()
        mock_file_logger.reset_mock()
        mock_subprocess.return_value.stdout = BASIC_META + INFO_META + FORMAT_META + REFERENCE_META + HEADER_LINE + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(VALIDATE_VCF_BODY))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), VALIDATE_VFC_RESPONSE)
        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://test_bucket/test_path.vcf', stdout=-1, stderr=-2, shell=True),  # nosec
            mock.call().wait(),
            mock.call('gsutil cat gs://test_bucket/test_path.vcf', stdout=-1, stderr=-2, shell=True),  # nosec
        ])
        mock_file_logger.info.assert_has_calls([
            mock.call('==> gsutil ls gs://test_bucket/test_path.vcf', self.manager_user),
            mock.call('==> gsutil cat gs://test_bucket/test_path.vcf', None),
        ])

        # Test a valid sharded VCF file path
        mock_subprocess.reset_mock()
        mock_file_exist_or_list_subproc = mock.MagicMock()
        mock_get_header_subproc = mock.MagicMock()
        mock_subprocess.side_effect = [mock_file_exist_or_list_subproc, mock_get_header_subproc]
        mock_file_exist_or_list_subproc.communicate.return_value = b'gs://test_bucket/test_path-001.vcf.gz\ngs://test_bucket/test_path-102.vcf.gz\n', None
        mock_get_header_subproc.stdout = BASIC_META + INFO_META + FORMAT_META + HEADER_LINE + DATA_LINES
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_SHARDED_DATA_PATH))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'fullDataPath': 'gs://test_bucket/test_path-*.vcf.gz', 'vcfSamples': ['HG00735', 'NA19675_1', 'NA19679']})
        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://test_bucket/test_path-*.vcf.gz', stdout=-1, stderr=-1, shell=True),  # nosec
            mock.call('gsutil cat -r 0-65536 gs://test_bucket/test_path-001.vcf.gz | gunzip -c -q - ', stdout=-1, stderr=-2, shell=True),  # nosec
        ])
        mock_file_logger.info.assert_has_calls([
            mock.call('==> gsutil ls gs://test_bucket/test_path-*.vcf.gz', self.manager_user),
            mock.call('==> gsutil cat -r 0-65536 gs://test_bucket/test_path-001.vcf.gz | gunzip -c -q - ', None),
        ])

        # Test logged in locally
        remove_token(
            self.manager_user)  # The user will look like having logged in locally after the access token is removed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         '/login/google-oauth2?next=/api/create_project_from_workspace/my-seqr-billing/anvil-no-project-workspace1/validate_vcf')

    @mock.patch('seqr.utils.file_utils.logger')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_get_anvil_igv_options(self, *args):
        url = reverse(get_anvil_igv_options, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME1])
        expected_options = [
            {'name': '/test.bam', 'value': 'gs://test_bucket/test.bam'},
            {'name': '/data/test.cram', 'value': 'gs://test_bucket/data/test.cram'},
        ]
        self._test_get_workspace_files(url, 'igv_options', expected_options, *args)

    @mock.patch('seqr.utils.file_utils.logger')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_get_anvil_vcf_list(self, *args):
        url = reverse(get_anvil_vcf_list, args=[TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME1])
        expected_files = [
            '/test.vcf', '/data/test.vcf.gz', '/data/test-101.vcf.gz', '/data/test-102.vcf.gz', '/sharded/test-*.vcf.gz',
        ]
        self._test_get_workspace_files(url, 'dataPathList', expected_files, *args)

    def _test_get_workspace_files(self, url, response_key, expected_files, mock_subprocess, mock_file_logger, mock_utils_logger):
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')
        mock_utils_logger.warning.assert_called_with('User does not have sufficient permissions for workspace {}/{}'
                                                     .format(TEST_WORKSPACE_NAMESPACE, TEST_WORKSPACE_NAME1),
                                                     self.collaborator_user)

        # Test gsutil error
        mock_subprocess.return_value.communicate.return_value = b'', b'-bash: gsutil: command not found.\nPlease check the path.\n'
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['error'], 'Run command failed: -bash: gsutil: command not found. Please check the path.')

        # Test empty bucket
        mock_subprocess.return_value.communicate.return_value = b'', None
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {response_key: []})
        mock_subprocess.assert_called_with('gsutil ls gs://test_bucket', stdout=-1, stderr=-1, shell=True)  # nosec
        mock_file_logger.info.assert_called_with('==> gsutil ls gs://test_bucket', self.manager_user)

        # Test a valid operation
        mock_subprocess.reset_mock()
        mock_file_logger.reset_mock()
        mock_subprocess.return_value.communicate.return_value = b'\n'.join([
            b'Warning: some packages are out of date',
            b'gs://test_bucket/test.vcf', b'gs://test_bucket/test.tsv',
            b'gs://test_bucket/test.bam', b'gs://test_bucket/test.bam.bai', b'gs://test_bucket/data/test.cram',
            # path with common prefix but not sharded VCFs
            b'gs://test_bucket/data/test.vcf.gz', b'gs://test_bucket/data/test-101.vcf.gz',
            b'gs://test_bucket/data/test-102.vcf.gz',
            # sharded VCFs
            b'gs://test_bucket/sharded/test-101.vcf.gz', b'gs://test_bucket/sharded/test-102.vcf.gz',
            b'gs://test_bucket/sharded/test-2345.vcf.gz\n'
        ]), None
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {response_key: expected_files})
        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://test_bucket', stdout=-1, stderr=-1, shell=True),  # nosec
            mock.call().communicate(),
            mock.call('gsutil ls gs://test_bucket/**', stdout=-1, stderr=-1, shell=True),  # nosec
            mock.call().communicate(),
        ])
        mock_file_logger.info.assert_has_calls([
            mock.call('==> gsutil ls gs://test_bucket', self.manager_user),
            mock.call('==> gsutil ls gs://test_bucket/**', self.manager_user),
        ])


class LoadAnvilDataAPITest(AirflowTestCase, AirtableTest):
    fixtures = ['users', 'social_auth', 'reference_data', '1kg_project']

    LOADING_PROJECT_GUID = f'P_{TEST_NO_PROJECT_WORKSPACE_NAME}'
    ADDITIONAL_REQUEST_COUNT = 1

    @staticmethod
    def _get_dag_variable_overrides(additional_tasks_check):
        variables = {
            'project': LoadAnvilDataAPITest.LOADING_PROJECT_GUID,
            'callset_path': 'test_path.vcf',
            'sample_source': 'AnVIL',
            'sample_type': 'WES',
            'dataset_type': 'SNV_INDEL',
        }
        if additional_tasks_check:
            variables.update({
                'project': PROJECT1_GUID,
                'reference_genome': 'GRCh37',
            })
        return variables

    def setUp(self):
        # Set up api responses
        responses.add(responses.POST, f'{MOCK_AIRTABLE_URL}/appUelDNM3BnWaR7M/AnVIL%20Seqr%20Loading%20Requests%20Tracking', status=400)
        patcher = mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_URL', MOCK_AIRTABLE_URL)
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
        patcher = mock.patch('seqr.utils.search.add_data_utils.logger')
        self.mock_add_data_utils_logger = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.load_uploaded_file')
        self.mock_load_file = patcher.start()
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.export_utils.mv_file_to_gs')
        self.mock_mv_file = patcher.start()
        self.mock_mv_file.return_value = True
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
        mock_tempdir = patcher.start()
        mock_tempdir.return_value.__enter__.return_value = TEMP_PATH
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.export_utils.open')
        self.mock_temp_open = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.logger')
        self.mock_api_logger = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.datetime')
        self.mock_datetime = patcher.start()
        self.mock_datetime.now.side_effect = lambda: datetime(2021, 3, 1, 0, 0, 0)
        self.addCleanup(patcher.stop)
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.apis.anvil_workspace_api.send_html_email')
        self.mock_send_email = patcher.start()
        self.addCleanup(patcher.stop)

        super().setUp()

    @mock.patch('seqr.models.Family._compute_guid', lambda family: f'F_{family.family_id}_{family.project.workspace_name[17:]}')
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
        self.mock_authorized_session.reset_mock()
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(workspace_namespace=TEST_WORKSPACE_NAMESPACE, workspace_name=TEST_NO_PROJECT_WORKSPACE_NAME)
        response_json = response.json()
        self.assertDictEqual({k: getattr(project, k) for k in project._meta.json_fields}, {
            'guid': response_json['projectGuid'],
            'name': TEST_NO_PROJECT_WORKSPACE_NAME,
            'description': 'A test project',
            'workspace_namespace': TEST_WORKSPACE_NAMESPACE,
            'workspace_name': TEST_NO_PROJECT_WORKSPACE_NAME,
            'has_case_review': False,
            'enable_hgmd': False,
            'is_demo': False,
            'all_user_demo': False,
            'consent_code': None,
            'created_date': mock.ANY,
            'last_modified_date': mock.ANY,
            'last_accessed_date': mock.ANY,
            'genome_version': '38',
            'is_mme_enabled': True,
            'mme_contact_institution': 'Broad Center for Mendelian Genomics',
            'mme_primary_data_owner': 'Test Manager User',
            'mme_contact_url': 'mailto:test_user_manager@test.com',
            'vlm_contact_email': 'test_user_manager@test.com',
        })

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
            NEW_PROJECT_SAMPLE_DATA, 'GRCh38', REQUEST_BODY)

    @responses.activate
    @mock.patch('seqr.views.utils.individual_utils.Individual._compute_guid')
    def test_add_workspace_data(self, mock_compute_indiv_guid):
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

        # Test requesting to load data from a workspace with no previously loaded data
        url = reverse(add_workspace_data, args=['R0002_empty'])
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'New data cannot be added to this project until the previously requested data is loaded',
        )

        url = reverse(add_workspace_data, args=[PROJECT1_GUID])
        self._test_errors(url, ['uploadedFileId', 'fullDataPath', 'vcfSamples'], TEST_WORKSPACE_NAME)

        # Test Individual ID exists in an omitted family
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA + INVALID_ADDED_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertListEqual(response_json['errors'], [
            'HG00731 already has loaded data and cannot be moved to a different family',
        ])

        # Test missing loaded samples
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'In order to load data for families with previously loaded data, new family samples must be joint called in a single VCF with all previously'
            ' loaded samples. The following samples were previously loaded in this project but are missing from the VCF:'
            '\nFamily 1: NA19678')

        # Test a valid operation
        mock_compute_indiv_guid.return_value = 'I0000020_hg00735'
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY_ADD_DATA))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'familiesByGuid', 'familyNotesByGuid', 'individualsByGuid'})
        self.assertSetEqual(set(response_json['individualsByGuid'].keys()), {'I0000020_hg00735', 'I000001_na19675', 'I000003_na19679'})
        self.assertSetEqual(set(response_json['familiesByGuid'].keys()), {'F000001_1', 'F000015_21'})
        self.assertEqual(list(response_json['familyNotesByGuid'].keys()), ['FAN000004_21_c_a_new_family'])

        self._assert_valid_operation(Project.objects.get(guid=PROJECT1_GUID))

        mock_compute_indiv_guid.side_effect = ['I0000021_na19675_1', 'I0000022_na19678', 'I0000023_hg00735']
        url = reverse(add_workspace_data, args=[PROJECT2_GUID])
        self._test_mv_file_and_triggering_dag_exception(
            url, {'guid': PROJECT2_GUID}, PROJECT2_SAMPLE_DATA, 'GRCh37', REQUEST_BODY_ADD_DATA2)

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
        self.assertListEqual(response_json['errors'], ['Missing required columns: Affected, HPO Terms, Sex'])

        self.mock_load_file.return_value = LOAD_SAMPLE_DATA + MISSING_REQUIRED_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertListEqual(response_json['errors'], ['Missing Sex in row #4', 'Missing Affected in row #4'])

        # test sample data error
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA + BAD_SAMPLE_DATA
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertListEqual(response_json['errors'], [
            'NA19674 is affected but has no HPO terms',
            'NA19681 has invalid HPO terms: HP:0100258',
            'NA19678 is the father of NA19674 but is not included. Make sure to create an additional record with NA19678 as the Individual ID',
        ])

        # test missing samples
        self.mock_load_file.return_value = LOAD_SAMPLE_DATA_EXTRA_SAMPLE
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['errors'],
                         ['The following samples are included in the pedigree file but are missing from the VCF: NA19678'])

        self.mock_load_file.return_value = LOAD_SAMPLE_DATA_NO_AFFECTED
        response = self.client.post(url, content_type='application/json', data=json.dumps(REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['errors'],['The following families do not have any affected individuals: 22'])

    def _assert_valid_operation(self, project, test_add_data=True):
        genome_version = 'GRCh37' if test_add_data else 'GRCh38'

        self.mock_api_logger.error.assert_not_called()

        self.assertEqual(self.mock_temp_open.call_count, 1)
        self.mock_temp_open.assert_called_with(f'{TEMP_PATH}/{project.guid}_pedigree.tsv', 'w')
        header = ['Project_GUID', 'Family_GUID', 'Family_ID', 'Individual_ID', 'Paternal_ID', 'Maternal_ID', 'Sex']
        if test_add_data:
            rows = [
                ['R0001_1kg', 'F000001_1', '1', 'NA19675_1', '', 'NA19679', 'F'],
                ['R0001_1kg', 'F000001_1', '1', 'NA19678', '', '', 'M'],
                ['R0001_1kg', 'F000001_1', '1', 'NA19679', '', '', 'F'],
                ['R0001_1kg', 'F000015_21', '21', 'HG00735', '', '', 'U']
            ]
        else:
            rows = [
                ['P_anvil-no-project-workspace1', 'F_1_workspace1', '1', 'NA19675_1', '', 'NA19679', 'F'],
                ['P_anvil-no-project-workspace1', 'F_1_workspace1', '1', 'NA19679', '', '', 'F'],
                ['P_anvil-no-project-workspace1', 'F_21_workspace1', '21', 'HG00735', '', '', 'U'],
            ]
        self.mock_temp_open.return_value.__enter__.return_value.write.assert_called_with(
            '\n'.join(['\t'.join(row) for row in [header] + rows])
        )

        gs_path = f'gs://seqr-loading-temp/v3.1/{genome_version}/SNV_INDEL/pedigrees/WES/'
        self.mock_mv_file.assert_called_with(
            f'{TEMP_PATH}/*', gs_path, self.manager_user
        )

        self.assert_airflow_loading_calls(additional_tasks_check=test_add_data)

        # create airtable record
        self.assertDictEqual(json.loads(responses.calls[-1].request.body), {'records': [{'fields': {
            'Requester Name': 'Test Manager User',
            'Requester Email': 'test_user_manager@test.com',
            'AnVIL Project URL': f'http://testserver/project/{project.guid}/project_page',
            'Initial Request Date': '2021-03-01',
            'Number of Samples': 4 if test_add_data else 3,
            'Status': 'Loading',
        }}]})
        self.assert_expected_airtable_headers(-1)

        dag_json = {
            'projects_to_run': [project.guid],
            'dataset_type': 'SNV_INDEL',
            'reference_genome': genome_version,
            'callset_path': 'gs://test_bucket/test_path.vcf',
            'sample_type': 'WES',
            'sample_source': 'AnVIL',
        }
        sample_summary = '3 new'
        if test_add_data:
            sample_summary += ' and 2 re-loaded'
        slack_message = """
        *test_user_manager@test.com* requested to load {sample_summary} WES samples ({version}) from AnVIL workspace *my-seqr-billing/{workspace_name}* at 
        gs://test_bucket/test_path.vcf to seqr project <http://testserver/project/{guid}/project_page|*{project_name}*> (guid: {guid})

        Pedigree files have been uploaded to gs://seqr-loading-temp/v3.1/{version}/SNV_INDEL/pedigrees/WES

        DAG LOADING_PIPELINE is triggered with following:
        ```{dag}```
    """.format(guid=project.guid, version=genome_version, workspace_name=project.workspace_name,
                   project_name=project.name, sample_summary=sample_summary,
               dag=json.dumps(dag_json, indent=4),
               )
        self.mock_slack.assert_called_with(
            SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL, slack_message,
        )
        self.mock_send_email.assert_not_called()

        # test database models
        family_model_data = list(Family.objects.filter(project=project).values('family_id', 'familynote__note'))
        self.assertEqual(len(family_model_data), 14 if test_add_data else 2)
        self.assertIn({
            'family_id': '1',
            'familynote__note':  '*\r\n                        Fåmily analysis nøtes\r\n*' if test_add_data else None,
        }, family_model_data)
        self.assertIn({'family_id': '21', 'familynote__note': 'a new family'}, family_model_data)

        individual_model_data = list(Individual.objects.filter(family__project=project).values(
            'family__family_id', 'individual_id', 'mother__individual_id', 'father__individual_id', 'sex', 'affected', 'notes',
            'features',
        ))
        self.assertEqual(len(individual_model_data), 15 if test_add_data else 3)
        self.assertIn({
            'family__family_id': '21', 'individual_id': 'HG00735', 'mother__individual_id': None,
            'father__individual_id': None, 'sex': 'U', 'affected': 'A', 'notes': None, 'features': [{'id': 'HP:0001508'}],
        }, individual_model_data)
        self.assertIn({
            'family__family_id': '1', 'individual_id': 'NA19675_1', 'mother__individual_id': 'NA19679',
            'father__individual_id': None, 'sex': 'F', 'affected': 'A', 'notes': 'A affected individual, test1-zsf',
            'features': [{'id': 'HP:0011675'}, {'id': 'HP:0012469'}],
        }, individual_model_data)
        self.assertIn({
            'family__family_id': '1', 'individual_id': 'NA19679', 'mother__individual_id': None,
            'father__individual_id': None, 'sex': 'F', 'affected': 'N', 'notes': 'a individual note', 'features': [],
        }, individual_model_data)

    def _test_mv_file_and_triggering_dag_exception(self, url, workspace, sample_data, genome_version, request_body, num_samples=None):
        # Test saving ID file exception
        responses.calls.reset()
        self.mock_authorized_session.reset_mock()
        self.mock_mv_file.side_effect = Exception('Something wrong while moving the file.')
        # Test triggering dag exception
        self.set_dag_trigger_error_response()

        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(**workspace)

        self.mock_add_data_utils_logger.error.assert_called_with(
            'Uploading Pedigrees failed. Errors: Something wrong while moving the file.',
            self.manager_user, detail={f'{project.guid}_pedigree': sample_data})
        self.mock_api_logger.error.assert_not_called()
        self.mock_airflow_logger.warning.assert_called_with(
            'LOADING_PIPELINE DAG is running and cannot be triggered again.', self.manager_user)
        self.mock_airtable_logger.error.assert_called_with(
            f'Airtable post "AnVIL Seqr Loading Requests Tracking" error: 400 Client Error: Bad Request for url: '
            f'{MOCK_AIRTABLE_URL}/appUelDNM3BnWaR7M/AnVIL%20Seqr%20Loading%20Requests%20Tracking', self.manager_user, detail=mock.ANY)

        slack_message_on_failure = """ERROR triggering AnVIL loading for project {guid}: LOADING_PIPELINE DAG is running and cannot be triggered again.
        
        DAG LOADING_PIPELINE should be triggered with following: 
        ```{dag}```
        """.format(
            guid=project.guid,
            dag=json.dumps({
                'projects_to_run': [project.guid],
                'dataset_type': 'SNV_INDEL',
                'reference_genome': genome_version,
                'callset_path': 'gs://test_bucket/test_path.vcf',
                'sample_type': 'WES',
                'sample_source': 'AnVIL',
            }, indent=4),
        )

        self.mock_slack.assert_any_call(
            SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, slack_message_on_failure,
        )
        self.mock_send_email.assert_not_called()
        self.assert_airflow_loading_calls(trigger_error=True)

        # Airtable record created with correct status
        self.assertDictEqual(json.loads(responses.calls[-1].request.body), {'records': [{'fields': {
            'Requester Name': 'Test Manager User',
            'Requester Email': 'test_user_manager@test.com',
            'AnVIL Project URL': f'http://testserver/project/{project.guid}/project_page',
            'Initial Request Date': '2021-03-01',
            'Number of Samples': num_samples or len(sample_data),
            'Status': 'Loading Requested',
        }}]})

    @mock.patch('seqr.views.apis.anvil_workspace_api.ANVIL_LOADING_DELAY_EMAIL_START_DATE', '2021-06-01')
    @responses.activate
    def test_create_project_from_workspace_loading_delay_email(self):
        url = reverse(create_project_from_workspace, args=[TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME])
        self.check_manager_login(url, login_redirect_url='/login/google-oauth2')

        # make sure the task id including the newly created project to avoid infinitely pulling the tasks
        self._add_dag_tasks_response([
            'R0006_anvil_no_project_workspace', 'R0007_anvil_no_project_workspace', 'R0008_anvil_no_project_workspace'])
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
        self._add_dag_tasks_response(['R0003_test', 'R0004_test'])
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
            internal retreat or closed for the winter break so we may not be able to load data until mid-January 
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
