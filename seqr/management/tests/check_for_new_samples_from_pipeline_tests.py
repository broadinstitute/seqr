from collections import defaultdict
from datetime import datetime
from django.core.management import call_command
from django.core.management.base import CommandError
import json
import mock
import responses

from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, AuthenticationTestCase, DifferentDbTransactionSupportMixin
from seqr.models import Project, Family, Individual, Sample, SavedVariant

SEQR_URL = 'https://seqr.broadinstitute.org/'
PROJECT_GUID = 'R0003_test'
EXTERNAL_PROJECT_GUID = 'R0004_non_analyst_project'

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
OLD_DATA_SAMPLE_GUID = 'S000143_na20885'

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
ANVIL_ERROR_TEXT_EMAIL = """Dear seqr user,

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
    '/seqr/seqr-hail-search-data/GRCh38/SNV_INDEL/runs/auto__2023-08-09/_CLICKHOUSE_LOAD_SUCCESS',
    '/seqr/seqr-hail-search-data/GRCh37/SNV_INDEL/runs/manual__2023-11-02/_CLICKHOUSE_LOAD_SUCCESS',
    '/seqr/seqr-hail-search-data/GRCh38/MITO/runs/auto__2024-08-12/_CLICKHOUSE_LOAD_SUCCESS',
    '/seqr/seqr-hail-search-data/GRCh38/GCNV/runs/auto__2024-09-14/_CLICKHOUSE_LOAD_SUCCESS',
    '/seqr/seqr-hail-search-data/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json',
    '/seqr/seqr-hail-search-data/GRCh38/SNV_INDEL/runs/hail_search_to_clickhouse_migration_WGS_R0877_neptune/_CLICKHOUSE_LOAD_SUCCESS',
]
RUN_PATHS = [
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-13/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-13/_ERRORS_REPORTED',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-13/validation_errors.json',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/validation_errors.json',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/auto__2023-08-09/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/auto__2023-08-09/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/auto__2023-08-09/_CLICKHOUSE_LOAD_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh37/SNV_INDEL/runs/manual__2023-11-02/',
    b'gs://seqr-hail-search-data/v3.1/GRCh37/SNV_INDEL/runs/manual__2023-11-02/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh37/SNV_INDEL/runs/manual__2023-11-02/_CLICKHOUSE_LOAD_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/MITO/runs/auto__2024-08-12/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/MITO/runs/auto__2024-08-12/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/MITO/runs/auto__2024-08-12/_CLICKHOUSE_LOAD_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/_CLICKHOUSE_LOAD_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/README.txt',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2025-03-14/',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2025-03-14/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/hail_search_to_clickhouse_migration_WGS_R0877_neptune/_SUCCESS',
    b'gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/hail_search_to_clickhouse_migration_WGS_R0877_neptune/_CLICKHOUSE_LOAD_SUCCESS',
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
    'sample_qc': {
        'NA20885': {
            'filtered_callrate': 1.0,
            'contamination_rate': 5.0,
            'percent_bases_at_20x': 90.0,
            'mean_coverage': 28.0,
            'filter_flags': ['coverage'],
            'pca_scores': [0.1 for _ in range(20)],
            'prob_afr': 0.02,
            'prob_ami': 0.0,
            'prob_amr': 0.02,
            'prob_asj': 0.9,
            'prob_eas': 0.0,
            'prob_fin': 0.0,
            'prob_mid': 0.0,
            'prob_nfe': 0.05,
            'prob_sas': 0.01,
            **{f'pop_PC{i + 1}': 0.1 for i in range(20)},
            'qc_gen_anc': 'oth',
            'sample_qc.call_rate': 1.0,
            'sample_qc.n_called': 30,
            'sample_qc.n_not_called': 0,
            'sample_qc.n_filtered': 0,
            'sample_qc.n_hom_ref': 17,
            'sample_qc.n_het': 3,
            'sample_qc.n_hom_var': 10,
            'sample_qc.n_non_ref': 13,
            'sample_qc.n_singleton': 0,
            'sample_qc.n_snp': 23,
            'sample_qc.n_insertion': 0,
            'sample_qc.n_deletion': 0,
            'sample_qc.n_transition': 13,
            'sample_qc.n_transversion': 10,
            'sample_qc.n_star': 0,
            'sample_qc.r_ti_tv': 1.3,
            'sample_qc.r_het_hom_var': 0.3,
            'sample_qc.r_insertion_deletion': None,
            'sample_qc.f_inbreeding.f_stat': -0.038400752079048056,
            'sample_qc.f_inbreeding.n_called': 30,
            'sample_qc.f_inbreeding.expected_homs': 27.11094199999999,
            'sample_qc.f_inbreeding.observed_homs': 27,
            'fail_n_snp': True,
            'fail_r_ti_tv': False,
            'fail_r_insertion_deletion': None,
            'fail_n_insertion': True,
            'fail_n_deletion': True,
            'fail_r_het_hom_var': False,
            'fail_call_rate': False,
            'qc_metrics_filters': ['n_deletion', 'n_insertion', 'n_snp'],
        },
        'NA19675_1': {
            'filtered_callrate': 1.0,
            'contamination_rate': 5.0,
            'percent_bases_at_20x': 90.0,
            'mean_coverage': 28.0,
            'filter_flags': ['callrate', 'contamination'],
            'pca_scores': [0.1 for _ in range(20)],
            'prob_afr': 0.02,
            'prob_ami': 0.0,
            'prob_amr': 0.02,
            'prob_asj': 0.9,
            'prob_eas': 0.0,
            'prob_fin': 0.0,
            'prob_mid': 0.0,
            'prob_nfe': 0.05,
            'prob_sas': 0.01,
            'qc_gen_anc': 'nfe',
            'sample_qc.call_rate': 1.0,
            'sample_qc.n_called': 30,
            'sample_qc.n_not_called': 0,
            'sample_qc.n_filtered': 0,
            'sample_qc.n_hom_ref': 17,
            'sample_qc.n_het': 3,
            'sample_qc.n_hom_var': 10,
            'sample_qc.n_non_ref': 13,
            'sample_qc.n_singleton': 0,
            'sample_qc.n_snp': 23,
            'sample_qc.n_insertion': 0,
            'sample_qc.n_deletion': 0,
            'sample_qc.n_transition': 13,
            'sample_qc.n_transversion': 10,
            'sample_qc.n_star': 0,
            'sample_qc.r_ti_tv': 1.3,
            'sample_qc.r_het_hom_var': 0.3,
            'sample_qc.r_insertion_deletion': None,
            'sample_qc.f_inbreeding.f_stat': -0.038400752079048056,
            'sample_qc.f_inbreeding.n_called': 30,
            'sample_qc.f_inbreeding.expected_homs': 27.11094199999999,
            'sample_qc.f_inbreeding.observed_homs': 27,
            'fail_n_snp': True,
            'fail_r_ti_tv': False,
            'fail_r_insertion_deletion': None,
            'fail_n_insertion': True,
            'fail_n_deletion': True,
            'fail_r_het_hom_var': False,
            'fail_call_rate': False,
            'qc_metrics_filters': [],
        }
    }
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
},
{
    'project_guids': ['R0002_empty'],
    'error_messages': ['Missing the following expected contigs:chr17'],
}, {
    'error': 'An unhandled error occurred during VCF ingestion',
}]

def mock_opened_file(index):
    m = mock.MagicMock()
    m.wait.return_value = 0
    m.stdout = [json.dumps(OPENED_RUN_JSON_FILES[index]).encode()]
    return m


@mock.patch('seqr.utils.file_utils.os.path.isfile', lambda *args: True)
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
        mock_rand_int.side_effect = [GUID_ID, GUID_ID, GUID_ID, GUID_ID, GCNV_GUID_ID, GCNV_GUID_ID, GCNV_GUID_ID, GCNV_GUID_ID, GUID_ID, GUID_ID, GUID_ID, GUID_ID]
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.management.commands.check_for_new_samples_from_pipeline.PIPELINE_DATA_DIR')
        mock_data_dir = patcher.start()
        mock_data_dir.__str__.return_value = self.MOCK_DATA_DIR
        self.addCleanup(patcher.stop)
        Sample.objects.filter(guid=OLD_DATA_SAMPLE_GUID).update(sample_type='WES')

    def _test_call(self, error_logs=None, run_loading_logs=None, num_runs=5):
        self._set_loading_files()
        self.reset_logs()

        call_command('check_for_new_samples_from_pipeline')

        single_call = num_runs < 5
        self._assert_expected_loading_file_calls(single_call=single_call)

        logs = self.LIST_FILE_LOGS[:1] + [(f'Loading new samples from {num_runs} run(s)', None)]
        runs = [
            ('GRCh38/SNV_INDEL', 'auto__2023-08-09'), ('GRCh37/SNV_INDEL', 'manual__2023-11-02'),
            ('GRCh38/MITO', 'auto__2024-08-12'), ('GRCh38/SV', 'auto__2024-09-14'),
            ('GRCh38/SNV_INDEL', 'hail_search_to_clickhouse_migration_WGS_R0877_neptune'),
        ]
        if single_call:
            runs = runs[:1]
        for data_type, version in runs:
            if 'hail_search_to_clickhouse_migration' in version:
                logs.append((f'Skipping ClickHouse migration {data_type}: {version}', None))
                continue
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
        logs += [] if single_call else [(log, None) for log in self.VALIDATION_LOGS]
        logs.append(('DONE', None))
        self.assert_json_logs(user=None, expected=logs)

        self.mock_redis.return_value.delete.assert_called_with('search_results__*', 'variant_lookup_results__*')

        num_calls = self._assert_expected_airtable_calls(bool(run_loading_logs), single_call)
        self.assertEqual(len(responses.calls), num_calls)

    def _additional_loading_logs(self, data_type, version):
        return []

    @mock.patch('seqr.views.utils.airtable_utils.BASE_URL', 'https://test-seqr.org/')
    @mock.patch('seqr.views.utils.airtable_utils.MAX_UPDATE_RECORDS', 2)
    @mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
    @mock.patch('seqr.utils.communication_utils.EmailMultiAlternatives')
    def test_command(self, mock_email, mock_temp_dir):
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
        create_snv_indel_samples_logs = [
            ('Loading 4 WES SNV_INDEL samples in 2 projects', None),
            ('create 4 Samples', {'dbUpdate': mock.ANY}),
            ('update 4 Samples', {'dbUpdate': mock.ANY}),
        ]
        update_sample_logs = [
            ('update 2 Individuals', {'dbUpdate': {
                'dbEntity': 'Individual', 'entityIds': ['I000001_na19675', 'I000015_na20885'],
                'updateFields': ['filter_flags', 'pop_platform_filters', 'population'],
                'updateType': 'bulk_update'}}
            ),
            ('Reloading saved variants in 2 projects', None),
            ('Reloading genotypes for 0 SNV_INDEL variants in family F000012_12', None),
            ('Updated 0 variants in 2 families for project Test Reprocessed Project', None),
            ('Reloading genotypes for 1 SNV_INDEL variants in family F000014_14', None),
            ('update 1 SavedVariants', {'dbUpdate': mock.ANY}),
            ('Updated 1 variants in 1 families for project Non-Analyst Project', None),
            ('Reload Summary: ', None),
            ('  Non-Analyst Project: Updated 1 variants', None),
        ]
        self._test_call(run_loading_logs={
            'GRCh38/SNV_INDEL': create_snv_indel_samples_logs + [
                ('update 1 Samples', {'dbUpdate': mock.ANY}),
                ('update 2 Familys', {'dbUpdate': mock.ANY}),
            ] + self.AIRTABLE_LOGS + [
                ('update 3 Familys', {'dbUpdate': mock.ANY}),
            ] + update_sample_logs,
            'GRCh38/MITO': [
                ('Loading 2 WGS MITO samples in 1 projects', None)
            ],
            'GRCh38/SV': [
                ('Loading 4 WES SV samples in 2 projects', None),
                ('create 4 Samples', {'dbUpdate': mock.ANY}),
                ('update 4 Samples', {'dbUpdate': mock.ANY}),
                ('update 3 Samples', {'dbUpdate': mock.ANY}),
                ('update 1 Familys', {'dbUpdate': mock.ANY}),
                ('Reloading saved variants in 2 projects', None),
                ('Updated 0 variants in 1 families for project 1kg project nåme with uniçøde', None),
                ('Updated 0 variants in 1 families for project Test Reprocessed Project', None),
                ('Reload Summary: ', None),
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

        self.assertFalse(Sample.objects.get(guid=OLD_DATA_SAMPLE_GUID).is_active)

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
            {REPLACED_SAMPLE_GUID, OLD_DATA_SAMPLE_GUID}
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

        # Test Individual model properly updated with sample qc results
        self.assertListEqual(
            list(Individual.objects.filter(
                guid__in=['I000001_na19675', 'I000015_na20885', 'I000016_na20888']).order_by('guid').values('filter_flags', 'pop_platform_filters', 'population')
            ),
            [{
                'filter_flags': {'callrate': 1.0, 'contamination': 5.0},
                'pop_platform_filters': {},
                'population': 'NFE'
            },{
                'filter_flags': {'coverage_exome': 90.0},
                'pop_platform_filters': {'n_deletion': 0, 'n_insertion': 0, 'n_snp': 23},
                'population': 'OTH'
            }, {
                'filter_flags': None,
                'pop_platform_filters': None,
                'population': 'SAS'
            }]
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

        saved_variant = SavedVariant.objects.get(key=100, family_id=14)
        self.assertDictEqual(saved_variant.genotypes, {'I000018_na21234': {
            'ab': 0.0, 'dp': 49, 'gq': 99, 'numAlt': 2, 'filters': [],
            'sampleId': 'NA21234', 'familyGuid': 'F000014_14', 'sampleType': 'WGS', 'individualGuid': 'I000018_na21234',
        }})

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
- fam14: Sample NA21987 has pedigree sex M but imputed sex F""",
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
            mock.call(body=TEXT_EMAIL_TEMPLATE.format(2, 'WES', 'Test Reprocessed Project'), subject='New WES data available in seqr', to=['test_user_manager@test.com']),
            mock.call().attach_alternative(HTML_EMAIL_TEMAPLTE.format(2, 'WES', PROJECT_GUID, 'Test Reprocessed Project'), 'text/html'),
            mock.call().send(),
            mock.call(body=self.PROJECT_EMAIL_TEXT, subject='New WES data available in seqr', to=['test_user_collaborator@test.com']),
            mock.call().attach_alternative(self.PROJECT_EMAIL_HTML, 'text/html'),
            mock.call().send(),
            mock.call(body=TEXT_EMAIL_TEMPLATE.format(0, 'WES SV', '1kg project nåme with uniçøde'), subject='New WES SV data available in seqr', to=['test_user_manager@test.com']),
            mock.call().attach_alternative(HTML_EMAIL_TEMAPLTE.format(0, 'WES SV', 'R0001_1kg', '1kg project nåme with uniçøde'), 'text/html'),
            mock.call().send(),
            mock.call(body=TEXT_EMAIL_TEMPLATE.format(1, 'WES SV', 'Test Reprocessed Project'), subject='New WES SV data available in seqr', to=['test_user_manager@test.com']),
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

        # Test reloading shared annotations is skipped if too many saved variants
        snv_indel_samples.delete()
        airtable_logs = self.AIRTABLE_LOGS[:-1]
        if self.AIRTABLE_LOGS:
            airtable_logs.append(('Fetched 1 AnVIL Seqr Loading Requests Tracking records from airtable', None))
        self._test_call(num_runs=2, run_loading_logs={
            'GRCh38/SNV_INDEL': create_snv_indel_samples_logs + airtable_logs + update_sample_logs,
        })


class LocalCheckNewSamplesTest(DifferentDbTransactionSupportMixin, AuthenticationTestCase, CheckNewSamplesTest):
    fixtures = ['users', '1kg_project', 'clickhouse_saved_variants']
    databases = '__all__'

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
        if not self.mock_glob.return_value:
            self.mock_glob.return_value = LOCAL_RUN_PATHS
        self.mock_open.return_value.__enter__.return_value.__iter__.side_effect = [
            iter([json.dumps(OPENED_RUN_JSON_FILES[i])]) for i in range(len(LOCAL_RUN_PATHS[2:-1]))
        ]
        self.mock_mkdir.reset_mock()

    def _assert_expected_loading_file_calls(self, single_call):
        self.mock_glob.assert_called_with('/seqr/seqr-hail-search-data/*/*/runs/*/*', recursive=False)
        self.mock_open.assert_has_calls([
            mock.call(LOCAL_RUN_PATHS[2], 'r'),
            *[mock.call(path.replace('_CLICKHOUSE_LOAD_SUCCESS', 'metadata.json'), 'r') for path in LOCAL_RUN_PATHS[3:-1]]
        ], any_order=True)
        self.assertEqual(self.mock_mkdir.call_count, 0 if single_call else 2)
        self.assertEqual(list(self.mock_written_files.keys()), [
            file.replace('validation_errors.json', '_ERRORS_REPORTED')
            for file in [LOCAL_RUN_PATHS[2], LOCAL_RUN_PATHS[7]]
        ])

    def _assert_expected_airtable_calls(self, *args, **kwargs):
        return 0


class AirtableCheckNewSamplesTest(AnvilAuthenticationTestCase, CheckNewSamplesTest):
    fixtures = ['users', '1kg_project', 'clickhouse_saved_variants']

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
        '==> gsutil ls gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/validation_errors.json',
        '==> gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/validation_errors.json',
        'Fetching AnVIL Seqr Loading Requests Tracking records 0-2 from airtable',
        'Fetched 1 AnVIL Seqr Loading Requests Tracking records from airtable',
        '==> gsutil mv /mock/tmp/* gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/',
        '==> gsutil ls gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json',
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

    @responses.activate
    def test_command(self, *args, **kwargs):
        responses.add(
            responses.GET,
            self.airtable_loading_tracking_url + self.AIRTABLE_LOADING_QUERY_TEMPLATE.format(EXTERNAL_PROJECT_GUID),
            json={'records': [{'id': 'rec12345', 'fields': {}}, {'id': 'rec67890', 'fields': {}}]})
        responses.add(
            responses.GET,
            self.airtable_loading_tracking_url + self.AIRTABLE_LOADING_QUERY_TEMPLATE.format(EXTERNAL_PROJECT_GUID),
            json={'records': [{'id': 'rec12345', 'fields': {}}]})
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
            'gsutil ls gs://seqr-hail-search-data/v3.1/GRCh37/MITO/runs/*/*', stdout=-1, stderr=-1, shell=True # nosec
        )

    def _set_reloading_loading_files(self):
        self.mock_ls_process.communicate.return_value = b'\n'.join(RUN_PATHS[6:8] + RUN_PATHS[15:17]), b''
        self.mock_subprocess.side_effect = [self.mock_ls_process]

    def _set_loading_files(self):
        responses.calls.reset()
        self.mock_subprocess.reset_mock()
        subprocesses = [self.mock_ls_process]
        for i in range(len(OPENED_RUN_JSON_FILES) - 1):
            subprocesses += [self.mock_mv_process, mock_opened_file(i)]
        subprocesses += [self.mock_mv_process, self.mock_mv_process,  mock_opened_file(-1), self.mock_mv_process]
        self.mock_subprocess.side_effect = subprocesses

    def _assert_expected_loading_file_calls(self, single_call):
        calls = [
            ('gsutil ls gs://seqr-hail-search-data/v3.1/*/*/runs/*/*', -1),
            ('gsutil ls gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/auto__2023-08-09/metadata.json', -2),
            ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/auto__2023-08-09/metadata.json', -2),
        ]
        if not single_call:
            calls += [
                ('gsutil ls gs://seqr-hail-search-data/v3.1/GRCh37/SNV_INDEL/runs/manual__2023-11-02/metadata.json', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh37/SNV_INDEL/runs/manual__2023-11-02/metadata.json', -2),
                ('gsutil ls gs://seqr-hail-search-data/v3.1/GRCh38/MITO/runs/auto__2024-08-12/metadata.json', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/MITO/runs/auto__2024-08-12/metadata.json', -2),
                ('gsutil ls gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/metadata.json', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/GCNV/runs/auto__2024-09-14/metadata.json', -2),
                ('gsutil ls gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/validation_errors.json', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/validation_errors.json', -2),
                ('gsutil mv /mock/tmp/* gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-14/', -2),
                ('gsutil ls gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json', -2),
                ('gsutil cat gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/validation_errors.json', -2),
                ('gsutil mv /mock/tmp/* gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/manual__2025-01-24/', -2),
            ]
        self.mock_subprocess.assert_has_calls(
            [mock.call(command, stdout=-1, stderr=stderr, shell=True) for (command, stderr) in calls] # nosec
        )

    def _additional_loading_logs(self, data_type, version):
        return [(f'==> gsutil ls gs://seqr-hail-search-data/v3.1/{data_type.replace("SV", "GCNV")}/runs/{version}/metadata.json', None),
                (f'==> gsutil cat gs://seqr-hail-search-data/v3.1/{data_type.replace("SV", "GCNV")}/runs/{version}/metadata.json', None)]

    def _assert_expected_airtable_calls(self, has_success_run, single_call):
        # Test request tracking updates for validation errors
        if single_call:
            fields = {'Status': 'Available in Seqr'}
        else:
            fields = {'Status': 'Loading request canceled', 'Notes': 'Callset validation failed'}
        update_loading_tracking_request = responses.calls[-1].request
        self.assertEqual(update_loading_tracking_request.url, self.airtable_loading_tracking_url)
        self.assertEqual(update_loading_tracking_request.method, 'PATCH')
        self.assertDictEqual(json.loads(update_loading_tracking_request.body), {'records': [
            {'id': 'rec12345', 'fields': fields},
        ]})

        if not has_success_run:
            return 8 if single_call else 2

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

        return 8 if single_call else 9
