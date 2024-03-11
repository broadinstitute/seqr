from datetime import datetime
from django.core.management import call_command
from django.core.management.base import CommandError
import json
import mock
import responses

from seqr.views.utils.test_utils import AnvilAuthenticationTestCase
from seqr.models import Project, Family, Individual, Sample, SavedVariant

SEQR_URL = 'https://seqr.broadinstitute.org/'
PROJECT_GUID = 'R0003_test'
EXTERNAL_PROJECT_GUID = 'R0004_non_analyst_project'
MOCK_HAIL_HOST = 'http://test-hail-host'

GUID_ID = 54321
NEW_SAMPLE_GUID_P3 = f'S{GUID_ID}_NA20888'
NEW_SAMPLE_GUID_P4 = f'S{GUID_ID}_NA21234'
REPLACED_SAMPLE_GUID = f'S{GUID_ID}_NA20885'
EXISTING_SAMPLE_GUID = 'S000154_na20889'
EXISTING_WGS_SAMPLE_GUID = 'S000144_na20888'
EXISTING_SV_SAMPLE_GUID = 'S000147_na21234'

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
INTERNAL_TEXT_EMAIL = """Dear seqr user,

This is to notify you that 2 new WES samples have been loaded in seqr project Test Reprocessed Project

All the best,
The seqr team"""
INTERNAL_HTML_EMAIL = f'Dear seqr user,<br /><br />' \
                      f'This is to notify you that 2 new WES samples have been loaded in seqr project ' \
                      f'<a href=https://seqr.broadinstitute.org/project/{PROJECT_GUID}/project_page>Test Reprocessed Project</a>' \
                      f'<br /><br />All the best,<br />The seqr team'


@mock.patch('seqr.utils.search.hail_search_utils.HAIL_BACKEND_SERVICE_HOSTNAME', MOCK_HAIL_HOST)
@mock.patch('seqr.views.utils.dataset_utils.random.randint', lambda *args: GUID_ID)
@mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_URL', 'http://testairtable')
@mock.patch('seqr.utils.search.add_data_utils.BASE_URL', SEQR_URL)
@mock.patch('seqr.utils.search.add_data_utils.SEQR_SLACK_ANVIL_DATA_LOADING_CHANNEL', 'anvil-data-loading')
@mock.patch('seqr.utils.search.add_data_utils.SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL', 'seqr-data-loading')
class CheckNewSamplesTest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    def setUp(self):
        patcher = mock.patch('seqr.management.commands.check_for_new_samples_from_pipeline.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.variant_utils.logger')
        self.mock_utils_logger = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.search.add_data_utils.safe_post_to_slack')
        self.mock_send_slack = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.subprocess.Popen')
        self.mock_subprocess = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.variant_utils.redis.StrictRedis')
        self.mock_redis = patcher.start()
        self.mock_redis.return_value.keys.side_effect = lambda pattern: [pattern]
        self.addCleanup(patcher.stop)
        super().setUp()

    def _test_success(self, path, metadata, dataset_type, sample_guids, reload_calls, reload_annotations_logs, has_additional_requests=False):
        self.mock_subprocess.return_value.stdout = [json.dumps(metadata).encode()]
        self.mock_subprocess.return_value.wait.return_value = 0

        call_command('check_for_new_samples_from_pipeline', path, 'auto__2023-08-08')

        self.mock_subprocess.assert_has_calls([mock.call(command, stdout=-1, stderr=-2, shell=True) for command in [
            f'gsutil ls gs://seqr-hail-search-data/v03/{path}/runs/auto__2023-08-08/_SUCCESS',
            f'gsutil cat gs://seqr-hail-search-data/v03/{path}/runs/auto__2023-08-08/metadata.json',
        ]], any_order=True)

        self.mock_logger.info.assert_has_calls([
            mock.call(f'Loading new samples from {path}: auto__2023-08-08'),
            mock.call(f'Loading {len(sample_guids)} WES {dataset_type} samples in 2 projects'),
        ] + [mock.call(log) for log in reload_annotations_logs] + [
            mock.call('DONE'),
        ])
        self.mock_logger.warining.assert_not_called()

        self.mock_redis.return_value.delete.assert_called_with('search_results__*', 'variant_lookup_results__*')
        self.mock_utils_logger.info.assert_has_calls([
            mock.call('Reset 2 cached results'),
            mock.call('Reloading saved variants in 2 projects'),
        ])

        # Test reload saved variants
        self.assertEqual(len(responses.calls), len(reload_calls) + (2 if has_additional_requests else 0))
        for i, call in enumerate(reload_calls):
            resp = responses.calls[i+(1 if has_additional_requests else 0)]
            self.assertEqual(resp.request.url, f'{MOCK_HAIL_HOST}:5000/search')
            self.assertEqual(resp.request.headers.get('From'), 'manage_command')
            self.assertDictEqual(json.loads(resp.request.body), call)

        # Tests Sample models created/updated
        updated_sample_models = Sample.objects.filter(guid__in=sample_guids)
        self.assertEqual(len(updated_sample_models), len(sample_guids))
        self.assertSetEqual({'WES'}, set(updated_sample_models.values_list('sample_type', flat=True)))
        self.assertSetEqual({dataset_type}, set(updated_sample_models.values_list('dataset_type', flat=True)))
        self.assertSetEqual({True}, set(updated_sample_models.values_list('is_active', flat=True)))
        self.assertSetEqual({'1kg.vcf.gz'}, set(updated_sample_models.values_list('elasticsearch_index', flat=True)))
        self.assertSetEqual({'auto__2023-08-08'}, set(updated_sample_models.values_list('data_source', flat=True)))
        self.assertSetEqual(
            {datetime.now().strftime('%Y-%m-%d')},
            {date.strftime('%Y-%m-%d') for date in updated_sample_models.values_list('loaded_date', flat=True)}
        )

    @mock.patch('seqr.views.utils.airtable_utils.logger')
    @mock.patch('seqr.utils.communication_utils.EmailMultiAlternatives')
    @responses.activate
    def test_command(self, mock_email, mock_airtable_utils):
        responses.add(
            responses.GET,
            "http://testairtable/appUelDNM3BnWaR7M/AnVIL%20Seqr%20Loading%20Requests%20Tracking?fields[]=Status&pageSize=2&filterByFormula=AND({AnVIL Project URL}='https://seqr.broadinstitute.org/project/R0004_non_analyst_project/project_page',OR(Status='Loading',Status='Loading Requested'))",
            json={'records': [{'id': 'rec12345', 'fields': {}}, {'id': 'rec67890', 'fields': {}}]})
        responses.add(responses.POST, f'{MOCK_HAIL_HOST}:5000/search', status=200, json={
            'results': [{'variantId': '12-48367227-TC-T', 'familyGuids': ['F000014_14'], 'updated_field': 'updated_value'}],
            'total': 1,
        })
        responses.add(responses.POST, f'{MOCK_HAIL_HOST}:5000/multi_lookup', status=200, json={
            'results': [{'variantId': '1-46859832-G-A', 'updated_new_field': 'updated_value', 'rsid': 'rs123'}],
        })

        # Test errors
        with self.assertRaises(CommandError) as ce:
            call_command('check_for_new_samples_from_pipeline')
        self.assertEqual(str(ce.exception), 'Error: the following arguments are required: path, version')

        with self.assertRaises(CommandError) as ce:
            call_command('check_for_new_samples_from_pipeline', 'GRCh38/SNV_INDEL', 'auto__2023-08-08')
        self.assertEqual(str(ce.exception), 'Run failed for GRCh38/SNV_INDEL: auto__2023-08-08, unable to load data')

        metadata = {
            'callsets': ['1kg.vcf.gz'],
            'sample_type': 'WES',
            'family_samples': {
                'F0000123_ABC': ['NA22882', 'NA20885'],
                'F000012_12': ['NA20888', 'NA20889'],
                'F000014_14': ['NA21234'],
            },
        }
        self.mock_subprocess.return_value.wait.return_value = 1
        self.mock_subprocess.return_value.stdout = [json.dumps(metadata).encode()]

        with self.assertRaises(CommandError) as ce:
            call_command('check_for_new_samples_from_pipeline', 'GRCh38/SNV_INDEL', 'auto__2023-08-08', '--allow-failed')
        self.assertEqual(
            str(ce.exception), 'Invalid families in run metadata GRCh38/SNV_INDEL: auto__2023-08-08 - F0000123_ABC')
        self.mock_logger.warning.assert_called_with('Loading for failed run GRCh38/SNV_INDEL: auto__2023-08-08')

        metadata['family_samples']['F000011_11'] = metadata['family_samples'].pop('F0000123_ABC')
        self.mock_subprocess.return_value.stdout = [json.dumps(metadata).encode()]
        self.mock_subprocess.return_value.wait.return_value = 0
        with self.assertRaises(CommandError) as ce:
            call_command('check_for_new_samples_from_pipeline', 'GRCh38/SNV_INDEL', 'auto__2023-08-08')
        self.assertEqual(
            str(ce.exception),
            'Data has genome version GRCh38 but the following projects have conflicting versions: R0003_test (GRCh37)')

        # Update fixture data to allow testing edge cases
        Project.objects.filter(id__in=[1, 3]).update(genome_version=38)
        sv = SavedVariant.objects.get(guid='SV0000002_1248367227_r0390_100')
        sv.saved_variant_json['genomeVersion'] = '38'
        sv.save()

        with self.assertRaises(ValueError) as ce:
            call_command('check_for_new_samples_from_pipeline', 'GRCh38/SNV_INDEL', 'auto__2023-08-08')
        self.assertEqual(str(ce.exception), 'Matches not found for sample ids: NA22882')

        metadata['family_samples']['F000011_11'] = metadata['family_samples']['F000011_11'][1:]

        # Test success
        self.mock_logger.reset_mock()
        self.mock_subprocess.reset_mock()
        search_body = {
            'genome_version': 'GRCh38', 'num_results': 1, 'variant_ids': [['12', 48367227, 'TC', 'T']], 'variant_keys': [],
        }
        self._test_success('GRCh38/SNV_INDEL', metadata, dataset_type='SNV_INDEL', sample_guids={
            EXISTING_SAMPLE_GUID, REPLACED_SAMPLE_GUID, NEW_SAMPLE_GUID_P3, NEW_SAMPLE_GUID_P4,
        }, has_additional_requests=True, reload_calls=[
            {**search_body, 'sample_data': {'SNV_INDEL': [
                {'individual_guid': 'I000017_na20889', 'family_guid': 'F000012_12', 'project_guid': 'R0003_test', 'affected': 'A', 'sample_id': 'NA20889'},
                {'individual_guid': 'I000016_na20888', 'family_guid': 'F000012_12', 'project_guid': 'R0003_test', 'affected': 'A', 'sample_id': 'NA20888'},
            ]}},
            {**search_body, 'sample_data': {'SNV_INDEL': [
                {'individual_guid': 'I000018_na21234', 'family_guid': 'F000014_14', 'project_guid': 'R0004_non_analyst_project', 'affected': 'A', 'sample_id': 'NA21234'},
            ]}},
        ], reload_annotations_logs=[
            'Reloading shared annotations for 3 saved variants (3 unique)', 'Fetched 1 additional variants', 'Updated 2 saved variants',
        ])

        old_data_sample_guid = 'S000143_na20885'
        self.assertFalse(Sample.objects.get(guid=old_data_sample_guid).is_active)

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
            {EXISTING_SAMPLE_GUID}
        )
        self.assertSetEqual(
            set(Individual.objects.get(guid='I000018_na21234').sample_set.values_list('guid', flat=True)),
            {EXISTING_SV_SAMPLE_GUID, NEW_SAMPLE_GUID_P4}
        )

        # Test Family models updated
        self.assertListEqual(list(Family.objects.filter(
            guid__in=['F000011_11', 'F000012_12']
        ).values('analysis_status', 'analysis_status_last_modified_date')), [
            {'analysis_status': 'I', 'analysis_status_last_modified_date': None},
            {'analysis_status': 'I', 'analysis_status_last_modified_date': None},
        ])
        self.assertEqual(Family.objects.get(guid='F000014_14').analysis_status, 'Rncc')

        # Test SavedVariant model updated
        multi_lookup_request = responses.calls[3].request
        self.assertEqual(multi_lookup_request.url, f'{MOCK_HAIL_HOST}:5000/multi_lookup')
        self.assertEqual(multi_lookup_request.headers.get('From'), 'manage_command')
        self.assertDictEqual(json.loads(multi_lookup_request.body), {
            'genome_version': 'GRCh38',
            'data_type': 'SNV_INDEL',
            'variant_ids': [['1', 1562437, 'G', 'C'], ['1', 46859832, 'G', 'A']],
        })

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
        self.assertEqual(len(annotation_updated_variant.saved_variant_json), 18)
        self.assertListEqual(annotation_updated_variant.saved_variant_json['familyGuids'], ['F000001_1'])

        annotation_updated_json = SavedVariant.objects.get(guid='SV0059956_11560662_f019313_1').saved_variant_json
        self.assertEqual(len(annotation_updated_json), 18)
        self.assertEqual(annotation_updated_json['updated_new_field'], 'updated_value')
        self.assertEqual(annotation_updated_json['rsid'], 'rs123')
        self.assertEqual(annotation_updated_json['mainTranscriptId'], 'ENST00000505820')
        self.assertEqual(len(annotation_updated_json['genotypes']), 3)

        self.mock_utils_logger.error.assert_not_called()
        self.mock_utils_logger.info.assert_has_calls([
            mock.call('Updated 0 variants for project Test Reprocessed Project'),
            mock.call('Updated 1 variants for project Non-Analyst Project'),
            mock.call('Reload Summary: '),
            mock.call('  Non-Analyst Project: Updated 1 variants'),
        ])

        # Test notifications
        self.assertEqual(self.mock_send_slack.call_count, 2)
        self.mock_send_slack.assert_has_calls([
            mock.call(
                'seqr-data-loading',
                f'2 new WES samples are loaded in {SEQR_URL}project/{PROJECT_GUID}/project_page\n```NA20888, NA20889```',
            ),
            mock.call(
                'anvil-data-loading',
                f'1 new WES samples are loaded in {SEQR_URL}project/{EXTERNAL_PROJECT_GUID}/project_page',
            ),
        ])

        self.assertEqual(mock_email.call_count, 2)
        mock_email.assert_has_calls([
            mock.call(body=INTERNAL_TEXT_EMAIL, subject='New data available in seqr', to=['test_user_manager@test.com']),
            mock.call().attach_alternative(INTERNAL_HTML_EMAIL, 'text/html'),
            mock.call().send(),
            mock.call(body=ANVIL_TEXT_EMAIL, subject='New data available in seqr', to=['test_user_collaborator@test.com']),
            mock.call().attach_alternative(ANVIL_HTML_EMAIL, 'text/html'),
            mock.call().send(),
        ])
        self.assertDictEqual(mock_email.return_value.esp_extra, {'MessageStream': 'seqr-notifications'})
        self.assertDictEqual(mock_email.return_value.merge_data, {})

        mock_airtable_utils.error.assert_called_with(
            'Airtable patch "AnVIL Seqr Loading Requests Tracking" error: Unable to identify record to update', None, detail={
                'or_filters': {'Status': ['Loading', 'Loading Requested']},
                'and_filters': {'AnVIL Project URL': 'https://seqr.broadinstitute.org/project/R0004_non_analyst_project/project_page'},
                'update': {'Status': 'Available in Seqr'}})

        self.assertEqual(self.manager_user.notifications.count(), 3)
        self.assertEqual(
            str(self.manager_user.notifications.first()), 'Test Reprocessed Project Loaded 2 new WES samples 0 minutes ago')
        self.assertEqual(self.collaborator_user.notifications.count(), 2)
        self.assertEqual(
            str(self.collaborator_user.notifications.first()), 'Non-Analyst Project Loaded 1 new WES samples 0 minutes ago')

        # Test reloading has no effect
        self.mock_logger.reset_mock()
        mock_email.reset_mock()
        self.mock_send_slack.reset_mock()
        sample_last_modified = Sample.objects.filter(
            last_modified_date__isnull=False).values_list('last_modified_date', flat=True).order_by('-last_modified_date')[0]

        call_command('check_for_new_samples_from_pipeline', 'GRCh38/SNV_INDEL', 'auto__2023-08-08')
        self.mock_logger.info.assert_called_with(f'Data already loaded for GRCh38/SNV_INDEL: auto__2023-08-08')
        mock_email.assert_not_called()
        self.mock_send_slack.assert_not_called()
        self.assertFalse(Sample.objects.filter(last_modified_date__gt=sample_last_modified).exists())

    @responses.activate
    def test_gcnv_command(self):
        responses.add(responses.POST, f'{MOCK_HAIL_HOST}:5000/search', status=400)
        metadata = {
            'callsets': ['1kg.vcf.gz'],
            'sample_type': 'WES',
            'family_samples': {'F000004_4': ['NA20872'], 'F000012_12': ['NA20889']},
        }
        self._test_success('GRCh37/GCNV', metadata, dataset_type='SV', sample_guids={f'S{GUID_ID}_NA20872', f'S{GUID_ID}_NA20889'}, reload_calls=[{
            'genome_version': 'GRCh37', 'num_results': 1, 'variant_ids': [], 'variant_keys': ['prefix_19107_DEL'],
            'sample_data': {'SV_WES': [{'individual_guid': 'I000017_na20889', 'family_guid': 'F000012_12', 'project_guid': 'R0003_test', 'affected': 'A', 'sample_id': 'NA20889'}]},
        }], reload_annotations_logs=['No additional saved variants to update'])

        self.mock_send_slack.assert_has_calls([
            mock.call(
                'seqr-data-loading', f'1 new WES SV samples are loaded in {SEQR_URL}project/R0001_1kg/project_page\n```NA20872```',
            ), mock.call(
                'seqr-data-loading', f'1 new WES SV samples are loaded in {SEQR_URL}project/{PROJECT_GUID}/project_page\n```NA20889```',
            ),
        ])

        self.mock_utils_logger.error.assert_called_with('Error in project Test Reprocessed Project: Bad Request')
        self.mock_utils_logger.info.assert_has_calls([
            mock.call('Reload Summary: '),
            mock.call('Skipped the following 1 project with no saved variants: 1kg project nåme with uniçøde'),
            mock.call('1 failed projects'),
            mock.call('  Test Reprocessed Project: Bad Request'),
        ])
