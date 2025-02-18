from collections import defaultdict
from datetime import datetime
from django.core.management import call_command
from django.core.management.base import CommandError
import json
import mock
import responses

from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, AuthenticationTestCase
from seqr.models import Project, Family, Individual, Sample, SavedVariant

SEQR_URL = 'https://seqr.broadinstitute.org/'
PROJECT_GUID = 'R0003_test'
EXTERNAL_PROJECT_GUID = 'R0004_non_analyst_project'
MOCK_HAIL_HOST = 'test-hail-host'
MOCK_HAIL_ORIGIN = f'http://{MOCK_HAIL_HOST}'

GUID_ID = 54321
GCNV_GUID_ID = 12345
NEW_SAMPLE_GUID_P3 = f'S00000{GUID_ID}_na20888'
NEW_SAMPLE_GUID_P4 = f'S00000{GUID_ID}_na21234'
REPLACED_SAMPLE_GUID = f'S00000{GUID_ID}_na20885'
EXISTING_INACTIVE_SAMPLE_GUID = 'S000154_na20889'
ACTIVE_SAMPLE_GUID = f'S00000{GUID_ID}_na20889'
EXISTING_WGS_SAMPLE_GUID = 'S000144_na20888'
EXISTING_SV_SAMPLE_GUID = 'S000147_na21234'
SAMPLE_GUIDS = [ACTIVE_SAMPLE_GUID, REPLACED_SAMPLE_GUID, NEW_SAMPLE_GUID_P3, NEW_SAMPLE_GUID_P4]
GCNV_SAMPLE_GUID = f'S00000{GCNV_GUID_ID}_na20889'
EXISTING_GCNV_SAMPLE_GUIDS = ['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733']
GCNV_SAMPLE_GUIDS = [f'S00000{GCNV_GUID_ID}_hg00731', f'S00000{GCNV_GUID_ID}_hg00732', f'S00000{GCNV_GUID_ID}_hg00733', GCNV_SAMPLE_GUID]

namespace_path = 'ext-data/anvil-non-analyst-project 1000 Genomes Demo'
anvil_link = f'<a href=https://anvil.terra.bio/#workspaces/{namespace_path}>{namespace_path}</a>'
seqr_link = f'<a href=https://seqr.broadinstitute.org/project/{EXTERNAL_PROJECT_GUID}/project_page>Non-Analyst Project</a>'
ANVIL_TEXT_EMAIL = f"""Dear seqr user,

We are following up on the request to load data from AnVIL on March 12, 2017.
We have loaded 1 new WES samples from the AnVIL workspace {namespace_path} to the corresponding seqr project Non-Analyst Project.
Let us know if you have any questions.

All the best,
The seqr team"""
ANVIL_HTML_EMAIL = f'Dear seqr user,<br /><br />' \
                   f'We are following up on the request to load data from AnVIL on March 12, 2017.<br />' \
                   f'We have loaded 1 new WES samples from the AnVIL workspace {anvil_link} to the corresponding seqr project {seqr_link}.' \
                   f'<br />Let us know if you have any questions.<br /><br />All the best,<br />The seqr team'
ANVIL_ERROR_TEXT_EMAIL = f"""Dear seqr user,

We are following up on the request to load data from AnVIL workspace ext-data/empty on March 12, 2017. This request could not be loaded due to the following error(s):
- Missing the following expected contigs:chr17
These errors often occur when a joint called VCF is not created in a supported manner. Please see our documentation for more information about supported calling pipelines and file formats. If you believe this error is incorrect and would like to request a manual review, please respond to this email.

All the best,
The seqr team"""
ANVIL_ERROR_HTML_EMAIL = f'Dear seqr user,<br /><br />' \
f'We are following up on the request to load data from AnVIL workspace {anvil_link.replace("anvil-non-analyst-project 1000 Genomes Demo", "empty")} on March 12, 2017. This request could not be loaded due to the following error(s):<br />' \
f'- Missing the following expected contigs:chr17<br />' \
f'These errors often occur when a joint called VCF is not created in a supported manner. ' \
f'Please see our <a href=https://storage.googleapis.com/seqr-reference-data/seqr-vcf-info.pdf>documentation</a> for more information about supported calling pipelines and file formats. If you believe this error is incorrect and would like to request a manual review, please respond to this email.'\
f'<br /><br />All the best,<br />The seqr team'
TEXT_EMAIL_TEMPLATE = """Dear seqr user,

This is to notify you that data for {} new {} samples has been loaded in seqr project {}

All the best,
The seqr team"""
HTML_EMAIL_TEMAPLTE = 'Dear seqr user,<br /><br />' \
                      'This is to notify you that data for {} new {} samples has been loaded in seqr project ' \
                      '<a href=https://seqr.broadinstitute.org/project/{}/project_page>{}</a>' \
                      '<br /><br />All the best,<br />The seqr team'

PDO_QUERY_FIELDS = '&'.join([f'fields[]={field}' for field in [
    'PDO', 'PDOStatus', 'SeqrLoadingDate', 'GATKShortReadCallsetPath', 'SeqrProjectURL', 'TerraProjectURL',
    'SequencingProduct', 'PDOName', 'SequencingSubmissionDate', 'SequencingCompletionDate', 'CallsetRequestedDate',
    'CallsetCompletionDate', 'Project', 'Metrics Checked', 'gCNV_SV_CallsetPath', 'DRAGENShortReadCallsetPath',
]])
AIRTABLE_SAMPLE_RECORDS = {
  'records': [
    {
      'id': 'rec2B6OGmQpAkQW3s',
      'fields': {
        'CollaboratorSampleID': 'NA19675_1',
        'PDOID': ['rec2B67GmXpAkQW8z', 'recW24C2CJW5lT64K'],
        'SeqrProject': ['https://test-seqr.org/project/R0002_empty/project_page', 'https://test-seqr.org/project/R0003_test/project_page'],
        'PDOStatus': ['Historic', 'Methods (Loading)'],
      },
    },
    {
      'id': 'recfMYDEZpPtzAIeV',
      'fields': {
        'CollaboratorSampleID': 'NA19678',
        'PDOID': ['recW24C2CJW5lT64K'],
        'SeqrProject': ['https://test-seqr.org/project/R0003_test/project_page'],
        'PDOStatus': ['Methods (Loading)'],
      },
    },
    {
      'id': 'rec2B67GmXpAkQW8z',
      'fields': {
        'CollaboratorSampleID': 'NA19679',
        'PDOID': ['rec2Nkg10N1KssPc3'],
        'SeqrProject': ['https://test-seqr.org/project/R0003_test/project_page'],
        'PDOStatus': ['Methods (Loading)'],
      },
    },
    {
      'id': 'rec2Nkg10N1KssPc3',
      'fields': {
        'SeqrCollaboratorSampleID': 'HG00731',
        'CollaboratorSampleID': 'VCGS_FAM203_621_D2',
        'PDOID': ['recW24C2CJW5lT64K'],
        'SeqrProject': ['https://test-seqr.org/project/R0003_test/project_page'],
        'PDOStatus': ['Methods (Loading)'],
      },
    },
    {
      'id': 'recrbZh9Hn1UFtMi2',
      'fields': {
        'SeqrCollaboratorSampleID': 'NA20888',
        'CollaboratorSampleID': 'NA20888_D1',
        'PDOID': ['recW24C2CJW5lT64K'],
        'SeqrProject': ['https://test-seqr.org/project/R0003_test/project_page'],
        'PDOStatus': ['Methods (Loading)'],
      },
    },
    {
      'id': 'rec2Nkg1fKssJc7',
      'fields': {
        'CollaboratorSampleID': 'NA20889',
        'PDOID': ['rec0RWBVfDVbtlBSL'],
        'SeqrProject': ['https://test-seqr.org/project/R0003_test/project_page'],
        'PDOStatus': ['Methods (Loading)'],
      },
    },
    {
      'id': 'rec2gRFoDBeHJc7',
      'fields': {
        'CollaboratorSampleID': 'NA20887',
        'PDOID': ['rec0RWBVfDVbtlBSL', 'rec2Nkg1fKgsJc7'],
        'SeqrProject': ['https://test-seqr.org/project/R0002_empty/project_page', 'https://test-seqr.org/project/R0003_test/project_page'],
        'PDOStatus': ['Methods (Loading)', 'Historic'],
      },
    },
]}
AIRTABLE_PDO_RECORDS = {
  'records': [
    {
      'id': 'recW24C2CJW5lT64K',
      'fields': {
        'PDO': 'PDO-1234',
        'SeqrProjectURL': 'https://test-seqr.org/project/R0003_test/project_page',
        'PDOStatus': 'Methods (Loading)',
        'PDOName': 'RGP_WGS_12',
      }
    },
  ]
}

LOCAL_RUN_PATHS = [
    '/seqr/seqr-hail-search-data/GRCh38/SNV_INDEL/runs/manual__2025-01-13/_ERRORS_REPORTED',
    '/seqr/seqr-hail-search-data/GRCh38/SNV_INDEL/runs/manual__2025-01-13/validation_errors.json',
    '/seqr/seqr-hail-search-data/GRCh38/SNV_INDEL/runs/manual__2025-01-14/validation_errors.json',
    '/seqr/seqr-hail-search-data/GRCh38/SNV_INDEL/runs/auto__2023-08-09/_SUCCESS',
    '/seqr/seqr-hail-search-data/GRCh37/SNV_INDEL/runs/manual__2023-11-02/_SUCCESS',
    '/seqr/seqr-hail-search-data/GRCh38/MITO/runs/auto__2024-08-12/_SUCCESS',
    '/seqr/seqr-hail-search-data/GRCh38/GCNV/runs/auto__2024-09-14/_SUCCESS',
    '/seqr/seqr-hail-search-data/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json',
]
RUN_PATHS = [
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-13/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-13/_ERRORS_REPORTED',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-13/validation_errors.json',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/validation_errors.json',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/auto__2023-08-09/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/auto__2023-08-09/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh37/SNV_INDEL/runs/manual__2023-11-02/',
    b'gs://seqr-hail-search-data/v3.1/GRCh37/SNV_INDEL/runs/manual__2023-11-02/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/MITO/runs/auto__2024-08-12/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/MITO/runs/auto__2024-08-12/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/README.txt',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json',
]
OPENED_RUN_JSON_FILES = [{
    'callsets': ['1kg.vcf.gz', 'new_samples.vcf.gz'],
    'sample_type': 'WES',
    'family_samples': {
        'F000011_11': ['NA20885'],
        'F000012_12': ['NA20888', 'NA20889'],
        'F000014_14': ['NA21234'],
    },
    'failed_family_samples': {
        'relatedness_check': {
            'F000001_1': {'reasons': [
                'Sample NA19679 has expected relation "parent" to NA19675 but has coefficients [0.0, 0.8505002045292791, 0.14949979547072176, 0.5747498977353613]',
                'Sample NA19678 has expected relation "sibling" to NA19675 but has coefficients [0.17424888135104177, 0.6041745754450025, 0.22157654320395614, 0.5236638309264574]',
            ]},
        },
        'sex_check': {
            'F000001_1': {'reasons': ['Sample NA19679 has pedigree sex F but imputed sex M']},
            'F000014_14': {'reasons': ['Sample NA21987 has pedigree sex M but imputed sex F']},
        },
        'missing_samples': {
            'F000002_2': {'reasons': ["Missing samples: {'HG00732', 'HG00733'}"]},
            'F000003_3': {'reasons': ["Missing samples: {'NA20870'}"]},
        },
    },
    'relatedness_check_file_path': 'gs://seqr-loading-temp/v3.1/GRCh38/SNV_INDEL/relatedness_check/test_callset_hash.tsv',
}, {
    'callsets': ['invalid_family.vcf'],
    'sample_type': 'WGS',
    'family_samples': {'F0000123_ABC': ['NA22882', 'NA20885']},
}, {
    'callsets': ['invalid_sample.vcf'],
    'sample_type': 'WGS',
    'family_samples': {'F000003_3': ['NA22882', 'NA20885']},
}, {
    'callsets': ['gcnv.bed.gz'],
    'sample_type': 'WES',
    'family_samples': {'F000002_2': ['HG00731', 'HG00732', 'HG00733'], 'F000012_12': ['NA20889']},
}, {
    'project_guids': ['R0002_empty'],
    'error_messages': ['Missing the following expected contigs:chr17'],
}, {
    'error': 'An unhandled error occurred during VCF ingestion',
}]

def mock_opened_file(index):
    m = mock.MagicMock()
    m.stdout = [json.dumps(OPENED_RUN_JSON_FILES[index]).encode()]
    return m


@mock.patch('seqr.utils.file_utils.os.path.isfile', lambda *args: True)
@mock.patch('seqr.utils.search.hail_search_utils.HAIL_BACKEND_SERVICE_HOSTNAME', MOCK_HAIL_HOST)
@mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_URL', 'http://testairtable')
@mock.patch('seqr.utils.communication_utils.BASE_URL', SEQR_URL)
@mock.patch('seqr.utils.search.add_data_utils.BASE_URL', SEQR_URL)
@mock.patch('seqr.utils.search.add_data_utils.SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL', 'anvil-data-loading')
@mock.patch('seqr.utils.search.add_data_utils.SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL', 'seqr-data-loading')
class CheckNewSamplesTest(object):

    def set_up(self):
        patcher = mock.patch('seqr.utils.communication_utils._post_to_slack')
        self.mock_send_slack = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.export_utils.open')
        self.mock_written_files = defaultdict(mock.MagicMock)
        mock_open_write_file = patcher.start()
        mock_open_write_file.side_effect = lambda file_name, *args: self.mock_written_files[file_name]
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.variant_utils.redis.StrictRedis')
        self.mock_redis = patcher.start()
        self.mock_redis.return_value.keys.side_effect = lambda pattern: [pattern]
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.models.random.randint')
        mock_rand_int = patcher.start()
        mock_rand_int.side_effect = [GUID_ID, GUID_ID, GUID_ID, GUID_ID, GCNV_GUID_ID, GCNV_GUID_ID, GCNV_GUID_ID, GCNV_GUID_ID]
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.management.commands.check_for_new_samples_from_pipeline.HAIL_SEARCH_DATA_DIR')
        mock_data_dir = patcher.start()
        mock_data_dir.__str__.return_value = self.MOCK_DATA_DIR
        self.addCleanup(patcher.stop)

    def _test_call(self, error_logs, reload_annotations_logs=None, run_loading_logs=None, reload_calls=None):
        self._set_loading_files()
        self.reset_logs()
        responses.calls.reset()

        call_command('check_for_new_samples_from_pipeline')

        self._assert_expected_loading_file_calls()

        logs = self.LIST_FILE_LOGS[:1] + [('Loading new samples from 4 run(s)', None)]
        for data_type, version in [
            ('GRCh38/SNV_INDEL', 'auto__2023-08-09'), ('GRCh37/SNV_INDEL', 'manual__2023-11-02'),
            ('GRCh38/MITO', 'auto__2024-08-12'), ('GRCh38/SV', 'auto__2024-09-14'),
        ]:
            logs.append((f'Loading new samples from {data_type}: {version}', None))
            logs += self._additional_loading_logs(data_type, version)
            if (run_loading_logs or {}).get(data_type):
                logs += run_loading_logs[data_type]
            if (error_logs or {}).get(version):
                logs.append((
                    f'Error loading {version}: {error_logs[version]}',
                    {'severity': 'ERROR', '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent'},
                ))
        logs.append(('Reset 2 cached results', None))
        logs += [(log, None) for log in reload_annotations_logs or []]
        logs += [(log, None) for log in self.VALIDATION_LOGS]
        logs.append(('DONE', None))
        self.assert_json_logs(user=None, expected=logs)

        self.mock_redis.return_value.delete.assert_called_with('search_results__*', 'variant_lookup_results__*')

        # Test reload saved variants
        num_airtable_loading_calls, num_airtable_validation_calls = self._assert_expected_airtable_calls(bool(reload_calls))
        if not reload_calls:
            self.assertEqual(len(responses.calls), num_airtable_validation_calls)
            return

        self.assertEqual(len(responses.calls), len(reload_calls) + 3 + num_airtable_loading_calls + num_airtable_validation_calls)
        for i, call in enumerate(reload_calls or []):
            resp = responses.calls[i+num_airtable_loading_calls]
            self.assertEqual(resp.request.url, f'{MOCK_HAIL_ORIGIN}:5000/search')
            self.assertEqual(resp.request.headers.get('From'), 'manage_command')
            self.assertDictEqual(json.loads(resp.request.body), call)

        for i, variant_id in enumerate([['1', 1562437, 'G', 'CA'], ['1', 46859832, 'G', 'A']]):
            multi_lookup_request = responses.calls[num_airtable_loading_calls+len(reload_calls)+i].request
            self.assertEqual(multi_lookup_request.url, f'{MOCK_HAIL_ORIGIN}:5000/multi_lookup')
            self.assertEqual(multi_lookup_request.headers.get('From'), 'manage_command')
            self.assertDictEqual(json.loads(multi_lookup_request.body), {
                'genome_version': 'GRCh38',
                'data_type': 'SNV_INDEL',
                'variant_ids': [variant_id],
            })

    def _additional_loading_logs(self, data_type, version):
        return []

    @mock.patch('seqr.management.commands.check_for_new_samples_from_pipeline.MAX_LOOKUP_VARIANTS', 1)
    @mock.patch('seqr.views.utils.airtable_utils.BASE_URL', 'https://test-seqr.org/')
    @mock.patch('seqr.views.utils.airtable_utils.MAX_UPDATE_RECORDS', 2)
    @mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
    @mock.patch('seqr.utils.communication_utils.EmailMultiAlternatives')
    @responses.activate
    def test_command(self, mock_email, mock_temp_dir):
        responses.add(responses.POST, f'{MOCK_HAIL_ORIGIN}:5000/search', status=200, json={
            'results': [{'variantId': '1-248367227-TC-T', 'familyGuids': ['F000014_14'], 'updated_field': 'updated_value'}],
            'total': 1,
        })
        responses.add(responses.POST, f'{MOCK_HAIL_ORIGIN}:5000/multi_lookup', status=200, json={
            'results': [{'variantId': '1-46859832-G-A', 'updated_new_field': 'updated_value', 'rsid': 'rs123'}],
        })
        responses.add(responses.POST, f'{MOCK_HAIL_ORIGIN}:5000/search', status=200, json={
            'results': [{'variantId': '1-248367227-TC-T', 'familyGuids': ['F000014_14'], 'updated_field': 'updated_value'}],
            'total': 1,
        })
        responses.add(responses.POST, f'{MOCK_HAIL_ORIGIN}:5000/search', status=400)

        # Test errors
        self._set_empty_loading_files()
        with self.assertRaises(CommandError) as ce:
            call_command('check_for_new_samples_from_pipeline', '--genome_version=GRCh37', '--dataset_type=MITO')
        self.assertEqual(str(ce.exception), 'No successful runs found for genome_version=GRCh37, dataset_type=MITO')
        self._assert_has_expected_empty_list_file_calls()

        self.reset_logs()
        call_command('check_for_new_samples_from_pipeline')
        self.assert_json_logs(user=None, expected=self.LIST_FILE_LOGS + [('No loaded data available', None)])
        mock_email.assert_not_called()
        self.mock_send_slack.assert_not_called()

        error_logs = {
            'auto__2023-08-09': 'Data has genome version GRCh38 but the following projects have conflicting versions: R0003_test (GRCh37)',
            'manual__2023-11-02': 'Invalid families in run metadata GRCh37/SNV_INDEL: manual__2023-11-02 - F0000123_ABC',
            'auto__2024-08-12': 'Data has genome version GRCh38 but the following projects have conflicting versions: R0001_1kg (GRCh37)',
            'auto__2024-09-14': 'Data has genome version GRCh38 but the following projects have conflicting versions: R0001_1kg (GRCh37), R0003_test (GRCh37)',
        }
        mock_temp_dir.return_value.__enter__.return_value = '/mock/tmp'
        self._test_call(error_logs=error_logs)
        self.assertEqual(Sample.objects.filter(guid__in=SAMPLE_GUIDS + GCNV_SAMPLE_GUIDS).count(), 0)

        # Update fixture data to allow testing edge cases
        Project.objects.filter(id__in=[1, 3]).update(genome_version=38)
        svs = SavedVariant.objects.filter(guid__in=['SV0000002_1248367227_r0390_100', 'SV0000006_1248367227_r0003_tes', 'SV0000007_prefix_19107_DEL_r00'])
        for sv in svs:
            sv.saved_variant_json['genomeVersion'] = '38'
            sv.save()

        # Test success
        self.mock_send_slack.reset_mock()
        mock_email.reset_mock()
        search_body = {
            'genome_version': 'GRCh38', 'num_results': 1, 'variant_ids': [['1', 248367227, 'TC', 'T']], 'variant_keys': [],
        }
        self._test_call(reload_calls=[
            {**search_body, 'sample_data': {'SNV_INDEL': [
                {'individual_guid': 'I000016_na20888', 'family_guid': 'F000012_12', 'project_guid': 'R0003_test', 'affected': 'A', 'sample_id': 'NA20888', 'sample_type': 'WES'},
                {'individual_guid': 'I000017_na20889', 'family_guid': 'F000012_12', 'project_guid': 'R0003_test', 'affected': 'A', 'sample_id': 'NA20889', 'sample_type': 'WES'},
            ]}},
            {**search_body, 'sample_data': {'SNV_INDEL': [
                {'individual_guid': 'I000018_na21234', 'family_guid': 'F000014_14', 'project_guid': 'R0004_non_analyst_project', 'affected': 'A', 'sample_id': 'NA21234', 'sample_type': 'WES'},
            ]}},
            {'genome_version': 'GRCh38', 'num_results': 1, 'variant_ids': [], 'variant_keys': ['prefix_19107_DEL'], 'sample_data': {'SV_WES': [
                {'individual_guid': 'I000017_na20889', 'family_guid': 'F000012_12', 'project_guid': 'R0003_test', 'affected': 'A', 'sample_id': 'NA20889', 'sample_type': 'WES'},
            ]}},
        ], reload_annotations_logs=[
            'Reloading shared annotations for 3 SNV_INDEL GRCh38 saved variants (3 unique)', 'Updated 1 SNV_INDEL GRCh38 saved variants', 'Fetched 1 additional variants in chromosome 1', 'Fetched 1 additional variants in chromosome 1', 'Updated 1 SNV_INDEL GRCh38 saved variants in chromosome 1',
            'Reloading shared annotations for 1 SV_WES GRCh38 saved variants (1 unique)', 'Fetched 1 additional variants in chromosome all', 'Updated 0 SV_WES GRCh38 saved variants in chromosome all',
        ], run_loading_logs={
            'GRCh38/SNV_INDEL': [
                ('Loading 4 WES SNV_INDEL samples in 2 projects', None),
                ('create 4 Samples', {'dbUpdate': mock.ANY}),
                ('update 4 Samples', {'dbUpdate': mock.ANY}),
                ('update 1 Samples', {'dbUpdate': mock.ANY}),
                ('update 2 Familys', {'dbUpdate': mock.ANY}),
            ] + self.AIRTABLE_LOGS + [
                ('update 3 Familys', {'dbUpdate': mock.ANY}),
                ('Reloading saved variants in 2 projects', None),
                ('Updated 0 variants in 2 families for project Test Reprocessed Project', None),
                ('update SavedVariant SV0000006_1248367227_r0004_non', {'dbUpdate': mock.ANY}),
                ('Updated 1 variants in 1 families for project Non-Analyst Project', None),
                ('Reload Summary: ', None),
                ('  Non-Analyst Project: Updated 1 variants', None),
            ],
            'GRCh38/MITO': [('Loading 2 WGS MITO samples in 1 projects', None)],
            'GRCh38/SV': [
                ('Loading 4 WES SV samples in 2 projects', None),
                ('create 4 Samples', {'dbUpdate': mock.ANY}),
                ('update 4 Samples', {'dbUpdate': mock.ANY}),
                ('update 3 Samples', {'dbUpdate': mock.ANY}),
                ('update 1 Familys', {'dbUpdate': mock.ANY}),
                ('Reloading saved variants in 2 projects', None),
                (mock.ANY, {'severity': 'ERROR', '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent'}),
                ('Error reloading variants in Test Reprocessed Project: Bad Request', {'severity': 'ERROR', '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent'}),
                ('Reload Summary: ', None),
                ('Skipped the following 1 project with no saved variants: 1kg project nåme with uniçøde', None),
                ('1 failed projects', None),
                ('  Test Reprocessed Project: Bad Request', None),
            ],
        }, error_logs={
            'manual__2023-11-02': 'Invalid families in run metadata GRCh37/SNV_INDEL: manual__2023-11-02 - F0000123_ABC',
            'auto__2024-08-12': 'Matches not found for sample ids: NA20885, NA22882',
        })

        # Tests Sample models created/updated
        snv_indel_samples = Sample.objects.filter(data_source='auto__2023-08-09')
        gcnv_samples = Sample.objects.filter(data_source='auto__2024-09-14')
        updated_sample_models = snv_indel_samples | gcnv_samples
        self.assertSetEqual({'WES'}, set(updated_sample_models.values_list('sample_type', flat=True)))
        self.assertSetEqual({True}, set(updated_sample_models.values_list('is_active', flat=True)))
        self.assertSetEqual(
            {datetime.now().strftime('%Y-%m-%d')},
            {date.strftime('%Y-%m-%d') for date in updated_sample_models.values_list('loaded_date', flat=True)}
        )

        self.assertSetEqual(set(snv_indel_samples.values_list('guid', flat=True)), set(SAMPLE_GUIDS))
        self.assertSetEqual({'SNV_INDEL'}, set(snv_indel_samples.values_list('dataset_type', flat=True)))
        self.assertSetEqual({'1kg.vcf.gz;new_samples.vcf.gz'}, set(snv_indel_samples.values_list('elasticsearch_index', flat=True)))

        self.assertSetEqual(set(gcnv_samples.values_list('guid', flat=True)), set(GCNV_SAMPLE_GUIDS))
        self.assertSetEqual({'SV'}, set(gcnv_samples.values_list('dataset_type', flat=True)))
        self.assertSetEqual({'gcnv.bed.gz'}, set(gcnv_samples.values_list('elasticsearch_index', flat=True)))

        old_data_sample_guid = 'S000143_na20885'
        self.assertFalse(Sample.objects.get(guid=old_data_sample_guid).is_active)

        previous_gcnv_samples = Sample.objects.filter(guid__in=EXISTING_GCNV_SAMPLE_GUIDS)
        self.assertEqual(len(previous_gcnv_samples), len(EXISTING_GCNV_SAMPLE_GUIDS))
        self.assertFalse(any(previous_gcnv_samples.values_list('is_active', flat=True)))

        # Previously loaded WGS data should be unchanged by loading WES data
        self.assertEqual(
            Sample.objects.get(guid=EXISTING_WGS_SAMPLE_GUID).last_modified_date.strftime('%Y-%m-%d'), '2017-03-13')

        # Previously loaded SV data should be unchanged by loading SNV_INDEL data
        sv_sample = Sample.objects.get(guid=EXISTING_SV_SAMPLE_GUID)
        self.assertEqual(sv_sample.last_modified_date.strftime('%Y-%m-%d'), '2018-03-13')
        self.assertTrue(sv_sample.is_active)

        # Test Individual models properly associated with Samples
        self.assertSetEqual(
            set(Individual.objects.get(guid='I000015_na20885').sample_set.values_list('guid', flat=True)),
            {REPLACED_SAMPLE_GUID, old_data_sample_guid}
        )
        self.assertSetEqual(
            set(Individual.objects.get(guid='I000016_na20888').sample_set.values_list('guid', flat=True)),
            {EXISTING_WGS_SAMPLE_GUID, NEW_SAMPLE_GUID_P3}
        )
        self.assertSetEqual(
            set(Individual.objects.get(guid='I000017_na20889').sample_set.values_list('guid', flat=True)),
            {EXISTING_INACTIVE_SAMPLE_GUID, ACTIVE_SAMPLE_GUID, GCNV_SAMPLE_GUID}
        )
        self.assertSetEqual(
            set(Individual.objects.get(guid='I000018_na21234').sample_set.values_list('guid', flat=True)),
            {EXISTING_SV_SAMPLE_GUID, NEW_SAMPLE_GUID_P4}
        )

        # Test Family models updated
        self.assertListEqual(list(Family.objects.filter(
            guid__in=['F000002_2', 'F000011_11', 'F000012_12']
        ).values('analysis_status', 'analysis_status_last_modified_date')), [
            {'analysis_status': 'I', 'analysis_status_last_modified_date': None},
            {'analysis_status': 'I', 'analysis_status_last_modified_date': None},
            {'analysis_status': 'I', 'analysis_status_last_modified_date': None},
        ])
        self.assertSetEqual(
            set(Family.objects.filter(guid__in=['F000001_1', 'F000003_3']).values_list('analysis_status', flat=True)),
            {'F'},
        )
        self.assertEqual(Family.objects.get(guid='F000014_14').analysis_status, 'Rncc')

        # Test SavedVariant model updated
        updated_variants = SavedVariant.objects.filter(saved_variant_json__updated_field='updated_value')
        self.assertEqual(len(updated_variants), 2)
        self.assertSetEqual(
            {v.guid for v in updated_variants},
            {'SV0000006_1248367227_r0004_non', 'SV0000002_1248367227_r0390_100'}
        )
        reloaded_variant = next(v for v in updated_variants if v.guid == 'SV0000006_1248367227_r0004_non')
        annotation_updated_variant = next(v for v in updated_variants if v.guid == 'SV0000002_1248367227_r0390_100')
        self.assertEqual(len(reloaded_variant.saved_variant_json), 3)
        self.assertListEqual(reloaded_variant.saved_variant_json['familyGuids'], ['F000014_14'])
        self.assertEqual(len(annotation_updated_variant.saved_variant_json), 19)
        self.assertListEqual(annotation_updated_variant.saved_variant_json['familyGuids'], ['F000001_1'])

        annotation_updated_json = SavedVariant.objects.get(guid='SV0059956_11560662_f019313_1').saved_variant_json
        self.assertEqual(len(annotation_updated_json), 18)
        self.assertEqual(annotation_updated_json['updated_new_field'], 'updated_value')
        self.assertEqual(annotation_updated_json['rsid'], 'rs123')
        self.assertEqual(annotation_updated_json['mainTranscriptId'], 'ENST00000505820')
        self.assertEqual(len(annotation_updated_json['genotypes']), 3)

        # Test notifications
        self.assertEqual(self.mock_send_slack.call_count, 7 + len(self.ADDITIONAL_SLACK_CALLS))
        self.mock_send_slack.assert_has_calls([
            mock.call(
                'seqr-data-loading',
                f'2 new WES samples are loaded in <{SEQR_URL}project/{PROJECT_GUID}/project_page|Test Reprocessed Project>\n```NA20888, NA20889```',
            ),
            ] + self.ADDITIONAL_SLACK_CALLS + [
            mock.call(
                'seqr_loading_notifications',
                """Encountered the following errors loading 1kg project nåme with uniçøde:

The following 1 families failed relatedness check:
- 1: Sample NA19679 has expected relation "parent" to NA19675 but has coefficients [0.0, 0.8505002045292791, 0.14949979547072176, 0.5747498977353613]; Sample NA19678 has expected relation "sibling" to NA19675 but has coefficients [0.17424888135104177, 0.6041745754450025, 0.22157654320395614, 0.5236638309264574]\n\nRelatedness check results: https://storage.cloud.google.com/seqr-loading-temp/v3.1/GRCh38/SNV_INDEL/relatedness_check/test_callset_hash.tsv

The following 1 families failed sex check:
- 1: Sample NA19679 has pedigree sex F but imputed sex M

The following 2 families failed missing samples:
- 2: Missing samples: {'HG00732', 'HG00733'}
- 3: Missing samples: {'NA20870'}""",
            ),
            mock.call(
                'seqr_loading_notifications',
                """Encountered the following errors loading Non-Analyst Project:

The following 1 families failed sex check:
- 14: Sample NA21987 has pedigree sex M but imputed sex F""",
            ),
            mock.call(
                'seqr-data-loading',
                f'0 new WES SV samples are loaded in <{SEQR_URL}project/R0001_1kg/project_page|1kg project nåme with uniçøde>',
            ), mock.call(
                'seqr-data-loading',
                f'1 new WES SV samples are loaded in <{SEQR_URL}project/{PROJECT_GUID}/project_page|Test Reprocessed Project>\n```NA20889```',
            ),
            mock.call(*self.SLACK_VALIDATION_CALL),
            mock.call('seqr_loading_notifications',
                      f"""Callset Validation Failed
*Projects:* MISSING FROM ERROR REPORT
*Reference Genome:* GRCh38
*Dataset Type:* SNV_INDEL
*Run ID:* manual__2025-01-24
*Validation Errors:* {{"error": "An unhandled error occurred during VCF ingestion"}}{self.SLACK_VALIDATION_MESSAGE}"""
        ),
        ])

        self.assertEqual(mock_email.call_count, 5 if self.ANVIL_EMAIL_CALLS else 4)
        mock_email.assert_has_calls([
            mock.call(body=TEXT_EMAIL_TEMPLATE.format(2, 'WES', 'Test Reprocessed Project'), subject='New data available in seqr', to=['test_user_manager@test.com']),
            mock.call().attach_alternative(HTML_EMAIL_TEMAPLTE.format(2, 'WES', PROJECT_GUID, 'Test Reprocessed Project'), 'text/html'),
            mock.call().send(),
            mock.call(body=self.PROJECT_EMAIL_TEXT, subject='New data available in seqr', to=['test_user_collaborator@test.com']),
            mock.call().attach_alternative(self.PROJECT_EMAIL_HTML, 'text/html'),
            mock.call().send(),
            mock.call(body=TEXT_EMAIL_TEMPLATE.format(0, 'WES SV', '1kg project nåme with uniçøde'), subject='New data available in seqr', to=['test_user_manager@test.com']),
            mock.call().attach_alternative(HTML_EMAIL_TEMAPLTE.format(0, 'WES SV', 'R0001_1kg', '1kg project nåme with uniçøde'), 'text/html'),
            mock.call().send(),
            mock.call(body=TEXT_EMAIL_TEMPLATE.format(1, 'WES SV', 'Test Reprocessed Project'), subject='New data available in seqr', to=['test_user_manager@test.com']),
            mock.call().attach_alternative(HTML_EMAIL_TEMAPLTE.format(1, 'WES SV', PROJECT_GUID, 'Test Reprocessed Project'), 'text/html'),
            mock.call().send(),
        ] + self.ANVIL_EMAIL_CALLS)
        self.assertDictEqual(mock_email.return_value.esp_extra, {'MessageStream': 'seqr-notifications'})
        self.assertDictEqual(mock_email.return_value.merge_data, {})

        self.assertEqual(self.manager_user.notifications.count(), 5)
        self.assertEqual(
            str(self.manager_user.notifications.first()), 'Test Reprocessed Project Loaded 1 new WES SV samples 0 minutes ago')
        self.assertEqual(self.collaborator_user.notifications.count(), 2)
        self.assertEqual(
            str(self.collaborator_user.notifications.first()), 'Non-Analyst Project Loaded 1 new WES samples 0 minutes ago')

        # Test reloading has no effect
        self._set_reloading_loading_files()
        self.reset_logs()
        mock_email.reset_mock()
        self.mock_send_slack.reset_mock()
        self.mock_redis.reset_mock()
        sample_last_modified = Sample.objects.filter(
            last_modified_date__isnull=False).values_list('last_modified_date', flat=True).order_by('-last_modified_date')[0]

        call_command('check_for_new_samples_from_pipeline')
        self.assert_json_logs(user=None, expected=self.LIST_FILE_LOGS[:1] + [('Data already loaded for all 2 runs', None)])
        mock_email.assert_not_called()
        self.mock_send_slack.assert_not_called()
        self.assertFalse(Sample.objects.filter(last_modified_date__gt=sample_last_modified).exists())
        self.mock_redis.return_value.delete.assert_not_called()

class LocalCheckNewSamplesTest(AuthenticationTestCase, CheckNewSamplesTest):
    fixtures = ['users', '1kg_project']

    ES_HOSTNAME = ''

    MOCK_DATA_DIR = '/seqr/seqr-hail-search-data'
    PROJECT_EMAIL_TEXT = TEXT_EMAIL_TEMPLATE.format(1, 'WES', 'Non-Analyst Project')
    PROJECT_EMAIL_HTML = HTML_EMAIL_TEMAPLTE.format(1, 'WES', EXTERNAL_PROJECT_GUID, 'Non-Analyst Project')
    ANVIL_EMAIL_CALLS = []

    LIST_FILE_LOGS = []
    AIRTABLE_LOGS = []
    VALIDATION_LOGS = []
    ADDITIONAL_SLACK_CALLS = [
        mock.call(
            'seqr-data-loading',
            f'1 new WES samples are loaded in <{SEQR_URL}project/{EXTERNAL_PROJECT_GUID}/project_page|Non-Analyst Project>\n```NA21234```',
        ),
    ]
    SLACK_VALIDATION_CALL = ('seqr_loading_notifications', """Callset Validation Failed
*Projects:* ['R0002_empty']
*Reference Genome:* GRCh38
*Dataset Type:* SNV_INDEL
*Run ID:* manual__2025-01-14
*Validation Errors:* ['Missing the following expected contigs:chr17']""")
    SLACK_VALIDATION_MESSAGE = ''

    def setUp(self):
        patcher = mock.patch('seqr.views.utils.export_utils.os.makedirs')
        self.mock_mkdir = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.glob.glob')
        self.mock_glob = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.open')
        self.mock_open = patcher.start()
        self.addCleanup(patcher.stop)
        self.set_up()
        super().setUp()

    def _set_empty_loading_files(self):
        self.mock_glob.return_value = []

    def _assert_has_expected_empty_list_file_calls(self):
        self.mock_glob.assert_called_with('/seqr/seqr-hail-search-data/GRCh37/MITO/runs/*/*', recursive=False)

    def _set_reloading_loading_files(self):
        self.mock_glob.return_value = [LOCAL_RUN_PATHS[3], LOCAL_RUN_PATHS[6]]

    def _set_loading_files(self):
        self.mock_glob.return_value = LOCAL_RUN_PATHS
        self.mock_open.return_value.__enter__.return_value.__iter__.side_effect = [
            iter([json.dumps(OPENED_RUN_JSON_FILES[i])]) for i in range(len(LOCAL_RUN_PATHS[2:]))
        ]
        self.mock_mkdir.reset_mock()

    def _assert_expected_loading_file_calls(self):
        self.mock_glob.assert_called_with('/seqr/seqr-hail-search-data/*/*/runs/*/*', recursive=False)
        self.mock_open.assert_has_calls([
            mock.call(LOCAL_RUN_PATHS[2], 'r'),
            *[mock.call(path.replace('_SUCCESS', 'metadata.json'), 'r') for path in LOCAL_RUN_PATHS[3:]]
        ], any_order=True)
        self.assertEqual(self.mock_mkdir.call_count, 2)
        self.assertEqual(list(self.mock_written_files.keys()), [
            file.replace('validation_errors.json', '_ERRORS_REPORTED')
            for file in [LOCAL_RUN_PATHS[2], LOCAL_RUN_PATHS[7]]
        ])

    def _assert_expected_airtable_calls(self, has_reload_calls):
        return 0, 0

class AirtableCheckNewSamplesTest(AnvilAuthenticationTestCase, CheckNewSamplesTest):
    fixtures = ['users', '1kg_project']

    airtable_samples_url = 'http://testairtable/app3Y97xtbbaOopVR/Samples'
    airtable_pdo_url = 'http://testairtable/app3Y97xtbbaOopVR/PDO'
    airtable_loading_tracking_url = "http://testairtable/appUelDNM3BnWaR7M/AnVIL%20Seqr%20Loading%20Requests%20Tracking"
    AIRTABLE_LOADING_QUERY_TEMPLATE = "?fields[]=Status&pageSize=2&filterByFormula=AND({{AnVIL Project URL}}='https://seqr.broadinstitute.org/project/{}/project_page',OR(Status='Loading',Status='Loading Requested'))"

    MOCK_DATA_DIR = 'gs://seqr-hail-search-data/v3.1'
    PROJECT_EMAIL_TEXT = ANVIL_TEXT_EMAIL
    PROJECT_EMAIL_HTML = ANVIL_HTML_EMAIL
    ANVIL_EMAIL_CALLS = [
        mock.call(body=ANVIL_ERROR_TEXT_EMAIL, subject='Error loading seqr data', to=['test_user_manager@test.com']),
        mock.call().attach_alternative(ANVIL_ERROR_HTML_EMAIL, 'text/html'),
        mock.call().send(),
    ]

    LIST_FILE_LOGS = [
        ('==> gsutil ls gs://seqr-hail-search-data/v3.1/*/*/runs/*/*', None),
        ('One or more URLs matched no objects', None),
    ]
    AIRTABLE_LOGS = [
        ('Fetching Samples records 0-2 from airtable', None),
        ('Fetched 7 Samples records from airtable', None),
        (f'Airtable patch "PDO" error: 400 Client Error: Bad Request for url: {airtable_pdo_url}', {
            'severity': 'ERROR',
            '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
            'detail': {'record_ids': ['rec0RWBVfDVbtlBSL', 'recW24C2CJW5lT64K'], 'update': {'PDOStatus': 'Available in seqr'}},
        }),
        ('Fetching PDO records 0-1 from airtable', None),
        ('Fetched 1 PDO records from airtable', None),
        ('Fetching AnVIL Seqr Loading Requests Tracking records 0-2 from airtable', None),
        ('Fetched 2 AnVIL Seqr Loading Requests Tracking records from airtable', None),
    ]
    VALIDATION_LOGS = [
        '==> gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/validation_errors.json',
        'Fetching AnVIL Seqr Loading Requests Tracking records 0-2 from airtable',
        'Fetched 1 AnVIL Seqr Loading Requests Tracking records from airtable',
        '==> gsutil mv /mock/tmp/* gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/',
        '==> gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json',
        '==> gsutil mv /mock/tmp/* gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/',
    ]
    ADDITIONAL_SLACK_CALLS = [
        mock.call(
            'anvil-data-loading',
            f'1 new WES samples are loaded in <{SEQR_URL}project/{EXTERNAL_PROJECT_GUID}/project_page|Non-Analyst Project>',
        ),
        mock.call(
            'seqr_loading_notifications',
            f'''Unable to identify Airtable "AnVIL Seqr Loading Requests Tracking" record to update

Record lookup criteria:
```
or_filters: {{"Status": ["Loading", "Loading Requested"]}}
and_filters: {{"AnVIL Project URL": "{SEQR_URL}project/{EXTERNAL_PROJECT_GUID}/project_page"}}
```

Desired update:
```
{{"Status": "Available in Seqr"}}
```''',
        ),
    ]
    SLACK_VALIDATION_CALL = ('anvil-data-loading', """Request to load data from *ext-data/empty* failed with the following error(s):
- Missing the following expected contigs:chr17
The following users have been notified: test_user_manager@test.com""")
    SLACK_VALIDATION_MESSAGE = '\nSee more at https://storage.cloud.google.com/seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json'

    def setUp(self):
        patcher = mock.patch('seqr.utils.file_utils.subprocess.Popen')
        self.mock_subprocess = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_ls_process = mock.MagicMock()
        self.mock_ls_process.communicate.return_value = b'\n'.join(RUN_PATHS), b''
        self.mock_mv_process = mock.MagicMock()
        self.mock_mv_process.wait.return_value = 0
        self.set_up()
        super().setUp()

    def test_command(self, *args, **kwargs):
        responses.add(
            responses.GET,
            self.airtable_loading_tracking_url + self.AIRTABLE_LOADING_QUERY_TEMPLATE.format(EXTERNAL_PROJECT_GUID),
            json={'records': [{'id': 'rec12345', 'fields': {}}, {'id': 'rec67890', 'fields': {}}]})
        responses.add(
            responses.GET,
            self.airtable_loading_tracking_url + self.AIRTABLE_LOADING_QUERY_TEMPLATE.format('R0002_empty'),
            json={'records': [{'id': 'rec12345', 'fields': {}}]})
        responses.add(
            responses.PATCH,
            self.airtable_loading_tracking_url,
            json={'records': [{'id': 'rec12345', 'fields': {}}]})
        responses.add(
            responses.GET,
            f"{self.airtable_samples_url}?fields[]=CollaboratorSampleID&fields[]=SeqrCollaboratorSampleID&fields[]=PDOStatus&fields[]=SeqrProject&fields[]=PDOID&pageSize=100&filterByFormula=AND(SEARCH('https://test-seqr.org/project/R0003_test/project_page',ARRAYJOIN({{SeqrProject}},';')),OR(SEARCH('Methods (Loading)',ARRAYJOIN(PDOStatus,';')),SEARCH('On hold for phenotips, but ready to load',ARRAYJOIN(PDOStatus,';'))))",
            json=AIRTABLE_SAMPLE_RECORDS)
        responses.add(
            responses.GET,
            f"{self.airtable_pdo_url}?{PDO_QUERY_FIELDS}&pageSize=100&filterByFormula=OR(RECORD_ID()='recW24C2CJW5lT64K')",
            json=AIRTABLE_PDO_RECORDS)
        responses.add(responses.PATCH, self.airtable_samples_url, json=AIRTABLE_SAMPLE_RECORDS)
        responses.add(responses.PATCH, self.airtable_pdo_url, status=400)
        responses.add_callback(responses.POST, self.airtable_pdo_url, callback=lambda request: (200, {}, json.dumps({
            'records': [{'id': f'rec{i}ABC123', **r} for i, r in enumerate(json.loads(request.body)['records'])]
        })))
        super().test_command(*args, **kwargs)

    def _set_empty_loading_files(self):
        self.mock_subprocess.return_value.communicate.return_value = b'', b'One or more URLs matched no objects'

    def _assert_has_expected_empty_list_file_calls(self):
        self.mock_subprocess.assert_called_with(
            'gsutil ls gs://seqr-hail-search-data/v3.1/GRCh37/MITO/runs/*/*', stdout=-1, stderr=-1, shell=True
        )

    def _set_reloading_loading_files(self):
        self.mock_ls_process.communicate.return_value = b'\n'.join([RUN_PATHS[6], RUN_PATHS[12]]), b''
        self.mock_subprocess.side_effect = [self.mock_ls_process]

    def _set_loading_files(self):
        self.mock_subprocess.reset_mock()
        self.mock_subprocess.side_effect = [self.mock_ls_process] + [
            mock_opened_file(i) for i in range(len(OPENED_RUN_JSON_FILES) - 1)
        ] + [self.mock_mv_process, mock_opened_file(-1), self.mock_mv_process]

    def _assert_expected_loading_file_calls(self):
        self.mock_subprocess.assert_has_calls(
            [mock.call(command, stdout=-1, stderr=stderr, shell=True) for (command, stderr) in [
                ('gsutil ls gs://seqr-hail-search-data/v3.1/*/*/runs/*/*', -1),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/auto__2023-08-09/metadata.json', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh37/SNV_INDEL/runs/manual__2023-11-02/metadata.json', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/MITO/runs/auto__2024-08-12/metadata.json', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/metadata.json', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/validation_errors.json', -2),
                ('gsutil mv /mock/tmp/* gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json', -2),
                ('gsutil mv /mock/tmp/* gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/', -2),
            ]])

    def _additional_loading_logs(self, data_type, version):
        return [(f'==> gsutil cat gs://seqr-hail-search-data/v3.1/{data_type.replace("SV", "GCNV")}/runs/{version}/metadata.json', None)]

    def _assert_expected_airtable_calls(self, has_reload_calls):
        # Test request tracking updates for validation errors
        update_loading_tracking_request = responses.calls[-1].request
        self.assertEqual(update_loading_tracking_request.url, self.airtable_loading_tracking_url)
        self.assertEqual(update_loading_tracking_request.method, 'PATCH')
        self.assertDictEqual(json.loads(update_loading_tracking_request.body), {'records': [
            {'id': 'rec12345', 'fields': {'Status': 'Loading request canceled', 'Notes': 'Callset validation failed'}},
        ]})
        if not has_reload_calls:
            return 0, 2

        # Test airtable PDO updates
        update_pdos_request = responses.calls[1].request
        self.assertEqual(update_pdos_request.url, self.airtable_pdo_url)
        self.assertEqual(update_pdos_request.method, 'PATCH')
        self.assertDictEqual(json.loads(update_pdos_request.body), {'records': [
            {'id': 'rec0RWBVfDVbtlBSL', 'fields': {'PDOStatus': 'Available in seqr'}},
            {'id': 'recW24C2CJW5lT64K', 'fields': {'PDOStatus': 'Available in seqr'}},
        ]})
        create_pdos_request = responses.calls[3].request
        self.assertEqual(create_pdos_request.url, self.airtable_pdo_url)
        self.assertEqual(create_pdos_request.method, 'POST')
        self.assertDictEqual(json.loads(create_pdos_request.body), {'records': [{'fields': {
            'PDO': 'PDO-1234_sr',
            'SeqrProjectURL': 'https://test-seqr.org/project/R0003_test/project_page',
            'PDOStatus': 'PM team (Relatedness checks)',
            'PDOName': 'RGP_WGS_12',
        }}]})
        update_samples_request = responses.calls[4].request
        self.assertEqual(update_samples_request.url, self.airtable_samples_url)
        self.assertEqual(update_samples_request.method, 'PATCH')
        self.assertDictEqual(json.loads(update_samples_request.body), {'records': [
            {'id': 'rec2B6OGmQpAkQW3s', 'fields': {'PDOID': ['rec0ABC123']}},
            {'id': 'rec2Nkg10N1KssPc3', 'fields': {'PDOID': ['rec0ABC123']}},
        ]})
        update_samples_request_2 = responses.calls[5].request
        self.assertEqual(update_samples_request_2.url, self.airtable_samples_url)
        self.assertEqual(update_samples_request_2.method, 'PATCH')
        self.assertDictEqual(json.loads(update_samples_request_2.body), {'records': [
            {'id': 'recfMYDEZpPtzAIeV', 'fields': {'PDOID': ['rec0ABC123']}},
        ]})
        return 7, 2
