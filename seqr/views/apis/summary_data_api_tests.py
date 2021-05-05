from datetime import datetime
from django.urls.base import reverse
import mock

from seqr.views.apis.summary_data_api import mme_details, success_story, saved_variants_page
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, MixAuthenticationTestCase


PROJECT_GUID = 'R0001_1kg'

EXPECTED_SUCCESS_STORY = {'project_guid': 'R0001_1kg', 'family_guid': 'F000013_13', 'success_story_types': ['A'], 'family_id': 'no_individuals', 'success_story': 'Treatment is now available on compassionate use protocol (nucleoside replacement protocol)', 'row_id': 'F000013_13'}

EXPECTED_MME_DETAILS_METRICS = {
    u'numberOfPotentialMatchesSent': 1,
    u'numberOfUniqueGenes': 4,
    u'numberOfCases': 4,
    u'numberOfRequestsReceived': 3,
    u'numberOfSubmitters': 2,
    u'numberOfUniqueFeatures': 4,
    u'dateGenerated': '2020-04-27'
}

SAVED_VARIANT_RESPONSE_KEYS = {
    'projectsByGuid', 'locusListsByGuid', 'savedVariantsByGuid', 'variantFunctionalDataByGuid', 'genesById',
    'variantNotesByGuid', 'individualsByGuid', 'variantTagsByGuid', 'familiesByGuid',
}


@mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json', lambda *args: None)
class SummaryDataAPITest(object):

    @mock.patch('seqr.views.apis.summary_data_api.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP', 'analysts')
    @mock.patch('matchmaker.matchmaker_utils.datetime')
    def test_mme_details(self, mock_datetime):
        url = reverse(mme_details)
        self.check_require_login(url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'genesById': {}, 'submissions': []})

        # Test behavior for non-analysts
        self.login_manager()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'genesById', 'submissions'})
        self.assertEqual(len(response_json['genesById']), 4)
        self.assertSetEqual(set(response_json['genesById'].keys()),
                            {'ENSG00000233750', 'ENSG00000227232', 'ENSG00000223972', 'ENSG00000186092'})
        self.assertEqual(len(response_json['submissions']), self.NUM_MANAGER_SUBMISSIONS)

        # Test analyst behavior
        self.login_analyst_user()
        mock_datetime.now.return_value = datetime(2020, 4, 27, 20, 16, 1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'metrics', 'genesById', 'submissions'})
        self.assertDictEqual(response_json['metrics'], EXPECTED_MME_DETAILS_METRICS)
        self.assertEqual(len(response_json['genesById']), 4)
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000233750', 'ENSG00000227232', 'ENSG00000223972', 'ENSG00000186092'})
        self.assertEqual(len(response_json['submissions']), 3)

    @mock.patch('seqr.views.apis.summary_data_api.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    def test_success_story(self, mock_analyst_group):
        url = reverse(success_story, args=['all'])
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'

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

    @mock.patch('seqr.views.apis.summary_data_api.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP', 'analysts')
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

# Tests for AnVIL access disabled
class LocalSummaryDataAPITest(AuthenticationTestCase, SummaryDataAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']
    NUM_MANAGER_SUBMISSIONS = 4
    MANAGER_VARIANT_GUID = 'SV0000006_1248367227_r0004_non'


def assert_has_expected_calls(self, users, access_level_call=False):
    calls = [mock.call(user) for user in users]
    self.mock_list_workspaces.assert_has_calls(calls)
    self.mock_get_ws_acl.assert_not_called()
    if access_level_call:
        self.mock_get_ws_access_level.assert_has_calls([
            mock.call(self.manager_user, 'my-seqr-billing', 'anvil-project 1000 Genomes Demo'),
            mock.call(self.manager_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de'),
            mock.call(self.manager_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de'),
            mock.call(self.manager_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de'),
        ], any_order=True)
    else:
        self.mock_get_ws_access_level.assert_not_called()

# Test for permissions from AnVIL only
class AnvilSummaryDataAPITest(AnvilAuthenticationTestCase, SummaryDataAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    NUM_MANAGER_SUBMISSIONS = 3
    MANAGER_VARIANT_GUID = None

    def test_mme_details(self):
        super(AnvilSummaryDataAPITest, self).test_mme_details()
        assert_has_expected_calls(self, [self.no_access_user, self.manager_user, self.analyst_user])

    def test_saved_variants_page(self):
        super(AnvilSummaryDataAPITest, self).test_saved_variants_page()
        assert_has_expected_calls(self, [
            self.no_access_user, self.manager_user, self.manager_user, self.analyst_user, self.analyst_user
        ], access_level_call=True)


# Test for permissions from AnVIL and local
class MixSummaryDataAPITest(MixAuthenticationTestCase, SummaryDataAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    NUM_MANAGER_SUBMISSIONS = 4
    MANAGER_VARIANT_GUID = 'SV0000006_1248367227_r0004_non'

    def test_mme_details(self):
        super(MixSummaryDataAPITest, self).test_mme_details()
        assert_has_expected_calls(self, [self.no_access_user, self.manager_user, self.analyst_user])

    def test_saved_variants_page(self):
        super(MixSummaryDataAPITest, self).test_saved_variants_page()
        assert_has_expected_calls(self, [
            self.no_access_user, self.manager_user, self.manager_user, self.analyst_user, self.analyst_user])

