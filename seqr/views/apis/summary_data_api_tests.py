from datetime import datetime
from django.urls.base import reverse
import json
import mock

from seqr.views.apis.summary_data_api import mme_details, success_story, saved_variants_page, hpo_summary_data, \
    bulk_update_family_analysed_by
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase
from seqr.models import FamilyAnalysedBy


PROJECT_GUID = 'R0001_1kg'

EXPECTED_SUCCESS_STORY = {'project_guid': 'R0001_1kg', 'family_guid': 'F000013_13', 'success_story_types': ['A'], 'family_id': 'no_individuals', 'success_story': 'Treatment is now available on compassionate use protocol (nucleoside replacement protocol)', 'row_id': 'F000013_13'}

EXPECTED_MME_DETAILS_METRICS = {
    u'numberOfPotentialMatchesSent': 1,
    u'numberOfUniqueGenes': 3,
    u'numberOfCases': 4,
    u'numberOfRequestsReceived': 3,
    u'numberOfSubmitters': 2,
    u'numberOfUniqueFeatures': 4,
    u'dateGenerated': '2020-04-27'
}

SAVED_VARIANT_RESPONSE_KEYS = {
    'projectsByGuid', 'locusListsByGuid', 'savedVariantsByGuid', 'variantFunctionalDataByGuid', 'genesById',
    'variantNotesByGuid', 'individualsByGuid', 'variantTagsByGuid', 'familiesByGuid', 'familyNotesByGuid',
    'mmeSubmissionsByGuid', 'transcriptsById',
}


@mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json', lambda *args: None)
class SummaryDataAPITest(object):

    @mock.patch('matchmaker.matchmaker_utils.datetime')
    def test_mme_details(self, mock_datetime):
        url = reverse(mme_details)
        self.check_require_login(url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'genesById': {}, 'savedVariantsByGuid': {}, 'submissions': []})

        # Test behavior for non-analysts
        self.login_manager()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        response_keys = {'genesById', 'submissions', 'savedVariantsByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertSetEqual(set(response_json['genesById'].keys()),
                            {'ENSG00000240361', 'ENSG00000223972', 'ENSG00000135953'})
        self.assertEqual(len(response_json['submissions']), self.NUM_MANAGER_SUBMISSIONS)

        # Test analyst behavior
        self.login_analyst_user()
        mock_datetime.now.return_value = datetime(2020, 4, 27, 20, 16, 1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        response_keys.add('metrics')
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertDictEqual(response_json['metrics'], EXPECTED_MME_DETAILS_METRICS)
        self.assertEqual(len(response_json['genesById']), 3)
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000240361', 'ENSG00000223972', 'ENSG00000135953'})
        self.assertEqual(len(response_json['submissions']), 3)

    def test_success_story(self):
        url = reverse(success_story, args=['all'])
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])

        self.assertEqual(len(response_json['rows']), 2)
        self.assertDictEqual(response_json['rows'][1], EXPECTED_SUCCESS_STORY)

        url = reverse(success_story, args=['A,T'])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])

        self.assertEqual(len(response_json['rows']), 1)
        self.assertDictEqual(response_json['rows'][0], EXPECTED_SUCCESS_STORY)

        self.check_no_analyst_no_access(url)

    @mock.patch('seqr.views.apis.summary_data_api.MAX_SAVED_VARIANTS', 1)
    def test_saved_variants_page(self):
        url = reverse(saved_variants_page, args=['Tier 1 - Novel gene and phenotype'])
        self.check_require_login(url)

        response = self.client.get('{}?gene=ENSG00000135953'.format(url))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {k: {} for k in SAVED_VARIANT_RESPONSE_KEYS})

        self.login_manager()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Select a gene to filter variants')

        gene_url = '{}?gene=ENSG00000135953'.format(url)
        response = self.client.get(gene_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), SAVED_VARIANT_RESPONSE_KEYS)
        expected_variant_guids = {
            'SV0000001_2103343353_r0390_100', 'SV0000007_prefix_19107_DEL_r00', 'SV0000006_1248367227_r0003_tes',
        }
        if self.MANAGER_VARIANT_GUID:
            expected_variant_guids.add(self.MANAGER_VARIANT_GUID)
        self.assertSetEqual(set(response_json['savedVariantsByGuid'].keys()), expected_variant_guids)
        self.assertSetEqual(
            set(response_json['projectsByGuid'][PROJECT_GUID].keys()),
            {'projectGuid', 'name', 'variantTagTypes', 'variantFunctionalTagTypes'},
        )

        # Test analyst behavior
        self.login_analyst_user()
        response = self.client.get(gene_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), SAVED_VARIANT_RESPONSE_KEYS)
        expected_variant_guids.discard(self.MANAGER_VARIANT_GUID)
        self.assertSetEqual(set(response_json['savedVariantsByGuid'].keys()), expected_variant_guids)

        all_tag_url = reverse(saved_variants_page, args=['ALL'])
        response = self.client.get('{}?gene=ENSG00000135953'.format(all_tag_url))
        self.assertEqual(response.status_code, 200)
        expected_variant_guids.add('SV0000002_1248367227_r0390_100')
        self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), expected_variant_guids)

    def test_hpo_summary_data(self):
        url = reverse(hpo_summary_data, args=['HP:0002011'])
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'data': []})

        self.login_manager()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'data'})
        self.assertListEqual(response_json['data'], [
            {
                'individualGuid': 'I000001_na19675',
                'displayName': 'NA19675_1',
                'features': [
                    {'id': 'HP:0001631', 'label': 'Defect in the atrial septum', 'category': 'HP:0025354'},
                    {'id': 'HP:0002011', 'label': 'Morphological abnormality of the central nervous system',
                     'category': 'HP:0000707', 'qualifiers': [
                        {'label': 'Infantile onset', 'type': 'age_of_onset'},
                        {'label': 'Mild', 'type': 'severity'},
                        {'label': 'Nonprogressive', 'type': 'pace_of_progression'}
                    ]},
                    {'id': 'HP:0001636', 'label': 'Tetralogy of Fallot', 'category': 'HP:0033127'},
                ],
                'familyId': '1',
                    'familyData': {
                    'projectGuid': PROJECT_GUID,
                    'genomeVersion': '37',
                    'familyGuid': 'F000001_1',
                    'analysisStatus': 'Q',
                    'displayName': '1',
                }
            },
            {
                'individualGuid': 'I000004_hg00731',
                'displayName': 'HG00731_a',
                'features': [
                    {'id': 'HP:0002011', 'label': 'Morphological abnormality of the central nervous system', 'category': 'HP:0000707'},
                    {'id': 'HP:0011675', 'label': 'Arrhythmia', 'category': 'HP:0001626'},
                ],
                'familyId': '2',
                'familyData': {
                    'projectGuid': PROJECT_GUID,
                    'genomeVersion': '37',
                    'familyGuid': 'F000002_2',
                    'analysisStatus': 'Q',
                    'displayName': '2_1',
                }
            },
        ])

    @mock.patch('seqr.views.apis.summary_data_api.load_uploaded_file')
    def test_bulk_update_family_analysed_by(self, mock_load_uploaded_file):
        url = reverse(bulk_update_family_analysed_by)
        self.check_analyst_login(url)

        mock_load_uploaded_file.return_value = [['foo', 'bar']]
        response = self.client.post(url, content_type='application/json', data=json.dumps(
            {'dataType': 'RNA', 'familiesFile': {'uploadedFileId': 'abc123'}}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Project and Family columns are required')

        mock_load_uploaded_file.return_value = [
            ['Project', 'Family ID'],
            ['1kg project n\u00e5me with uni\u00e7\u00f8de', '1'],
            ['Test Reprocessed Project', '12'],
            ['Test Reprocessed Project', 'not_a_family'],
            ['not_a_project', '2'],
        ]
        created_time = datetime.now()
        response = self.client.post(url, content_type='application/json', data=json.dumps(
            {'dataType': 'RNA', 'familiesFile': {'uploadedFileId': 'abc123'}}))
        self.assertDictEqual(response.json(), {
            'warnings': [
                'No match found for the following families: not_a_family (Test Reprocessed Project), 2 (not_a_project)'
            ],
            'info': ['Updated "analysed by" for 2 families'],
        })

        models = FamilyAnalysedBy.objects.filter(last_modified_date__gte=created_time)
        self.assertEqual(len(models), 2)
        self.assertSetEqual({fab.data_type for fab in models}, {'RNA'})
        self.assertSetEqual({fab.created_by for fab in models}, {self.analyst_user})
        self.assertSetEqual({fab.family.family_id for fab in models}, {'1', '12'})

        self.check_no_analyst_no_access(url)

# Tests for AnVIL access disabled
class LocalSummaryDataAPITest(AuthenticationTestCase, SummaryDataAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']
    NUM_MANAGER_SUBMISSIONS = 4
    MANAGER_VARIANT_GUID = 'SV0000006_1248367227_r0004_non'


def assert_has_expected_calls(self, users, skip_group_call_idxs=None):
    calls = [mock.call(user) for user in users]
    self.mock_list_workspaces.assert_has_calls(calls)
    group_calls = [call for i, call in enumerate(calls) if i in skip_group_call_idxs] if skip_group_call_idxs else calls
    self.mock_get_groups.assert_has_calls(group_calls)
    self.mock_get_ws_acl.assert_not_called()
    self.mock_get_group_members.assert_not_called()
    self.mock_get_ws_access_level.assert_not_called()

# Test for permissions from AnVIL only
class AnvilSummaryDataAPITest(AnvilAuthenticationTestCase, SummaryDataAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    NUM_MANAGER_SUBMISSIONS = 4
    MANAGER_VARIANT_GUID = 'SV0000006_1248367227_r0004_non'

    def test_mme_details(self, *args):
        super(AnvilSummaryDataAPITest, self).test_mme_details(*args)
        assert_has_expected_calls(self, [self.no_access_user, self.manager_user, self.analyst_user])

    def test_saved_variants_page(self):
        super(AnvilSummaryDataAPITest, self).test_saved_variants_page()
        assert_has_expected_calls(self, [
            self.no_access_user, self.manager_user, self.manager_user, self.analyst_user, self.analyst_user
        ], skip_group_call_idxs=[2])
