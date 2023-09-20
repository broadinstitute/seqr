from datetime import datetime
from django.urls.base import reverse
import json
import mock
import responses

from seqr.views.apis.summary_data_api import mme_details, success_story, saved_variants_page, hpo_summary_data, \
    bulk_update_family_analysed_by, sample_metadata_export
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, AirtableTest
from seqr.models import FamilyAnalysedBy
from settings import AIRTABLE_URL


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

EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW = {
    "project_guid": "R0003_test",
    "num_saved_variants": 2,
    "solve_state": "Tier 1",
    "sample_id": "NA20889",
    "Gene_Class-1": "Tier 1 - Candidate",
    "Gene_Class-2": "Tier 1 - Candidate",
    "inheritance_description-1": "Autosomal recessive (compound heterozygous)",
    "inheritance_description-2": "Autosomal recessive (compound heterozygous)",
    "hpo_absent": "",
    "novel_mendelian_gene-1": "Y",
    "novel_mendelian_gene-2": "Y",
    "hgvsc-1": "c.3955G>A",
    "date_data_generation": "2017-02-05",
    "Zygosity-1": "Heterozygous",
    "Zygosity-2": "Heterozygous",
    "Ref-1": "TC",
    "sv_type-2": "Deletion",
    "sv_name-2": "DEL:chr12:49045487-49045898",
    "Chrom-2": "12",
    "Pos-2": "49045487",
    "maternal_id": "",
    "paternal_id": "",
    "hgvsp-1": "c.1586-17C>G",
    "project_id": "Test Reprocessed Project",
    "Pos-1": "248367227",
    "data_type": "WES",
    "family_guid": "F000012_12",
    "congenital_status": "Unknown",
    "family_history": "Yes",
    "hpo_present": "HP:0011675 (Arrhythmia)|HP:0001509 ()",
    "Transcript-1": "ENST00000505820",
    "ancestry": "Ashkenazi Jewish",
    "phenotype_group": "",
    "sex": "Female",
    "Chrom-1": "1",
    "Alt-1": "T",
    "Gene-1": "OR4G11P",
    "pmid_id": None,
    "phenotype_description": None,
    "affected_status": "Affected",
    "family_id": "12",
    "MME": "Y",
    "subject_id": "NA20889",
    "proband_relationship": "",
    "consanguinity": "None suspected",
}
EXPECTED_SAMPLE_METADATA_ROW = {
    "dbgap_submission": "No",
    "dbgap_study_id": "",
    "dbgap_subject_id": "",
    "multiple_datasets": "No",
}
EXPECTED_SAMPLE_METADATA_ROW.update(EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW)

AIRTABLE_SAMPLE_RECORDS = {
  "records": [
    {
      "id": "rec2B6OGmQpAkQW3s",
      "fields": {
        "SeqrCollaboratorSampleID": "VCGS_FAM203_621_D1",
        "CollaboratorSampleID": "NA19675",
        "Collaborator": ["recW24C2CJW5lT64K"],
        "dbgap_study_id": "dbgap_stady_id_1",
        "dbgap_subject_id": "dbgap_subject_id_1",
        "dbgap_sample_id": "SM-A4GQ4",
        "SequencingProduct": [
          "Mendelian Rare Disease Exome"
        ],
        "dbgap_submission": [
          "WES",
          "Array"
        ]
      },
      "createdTime": "2019-09-09T19:21:12.000Z"
    },
    {
      "id": "rec2Nkg10N1KssPc3",
      "fields": {
        "SeqrCollaboratorSampleID": "HG00731",
        "CollaboratorSampleID": "NA20885",
        "Collaborator": ["reca4hcBnbA2cnZf9"],
        "dbgap_study_id": "dbgap_stady_id_2",
        "dbgap_subject_id": "dbgap_subject_id_2",
        "dbgap_sample_id": "SM-JDBTT",
        "SequencingProduct": [
          "Standard Germline Exome v6 Plus GSA Array"
        ],
        "dbgap_submission": [
          "WES",
          "Array"
        ]
      },
      "createdTime": "2019-07-16T18:23:21.000Z"
    }
]}
PAGINATED_AIRTABLE_SAMPLE_RECORDS = {
    'offset': 'abc123',
    'records': [{
      'id': 'rec2B6OGmQpfuRW5z',
      'fields': {
        'CollaboratorSampleID': 'NA19675',
        'Collaborator': ['recW24C2CJW5lT64K'],
        'dbgap_study_id': 'dbgap_study_id_2',
        'dbgap_subject_id': 'dbgap_subject_id_1',
        'dbgap_sample_id': 'SM-A4GQ4',
        'SequencingProduct': [
          'Mendelian Rare Disease Exome'
        ],
        'dbgap_submission': [
          'WES',
          'Array'
        ]
      },
      'createdTime': '2019-09-09T19:21:12.000Z'
    }
]}

AIRTABLE_COLLABORATOR_RECORDS = {
    "records": [
        {
            "id": "recW24C2CJW5lT64K",
            "fields": {
                "CollaboratorID": "Hildebrandt",
            }
        },
        {
            "id": "reca4hcBnbA2cnZf9",
            "fields": {
                "CollaboratorID": "Seidman",
            }
        }
    ]
}


@mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json', lambda *args: None)
class SummaryDataAPITest(AirtableTest):

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

        multi_tag_url = reverse(saved_variants_page, args=['Review;Tier 1 - Novel gene and phenotype'])
        response = self.client.get('{}?gene=ENSG00000135953'.format(multi_tag_url))
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), {'SV0000001_2103343353_r0390_100'})

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

    @mock.patch('seqr.views.utils.airtable_utils.MAX_OR_FILTERS', 2)
    @mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_API_KEY', 'mock_key')
    @mock.patch('seqr.views.utils.airtable_utils.is_google_authenticated')
    @responses.activate
    def test_sample_metadata_export(self, mock_google_authenticated):
        mock_google_authenticated.return_value = False
        url = reverse(sample_metadata_export, args=['R0003_test'])
        self.check_analyst_login(url)

        unauthorized_project_url = reverse(sample_metadata_export, args=['R0004_non_analyst_project'])
        response = self.client.get(unauthorized_project_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')
        mock_google_authenticated.return_value = True

        # Test invalid airtable responses
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), status=402)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 402)

        responses.reset()
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertIn(response.json()['error'], ['Unable to retrieve airtable data: No JSON object could be decoded',
                                                 'Unable to retrieve airtable data: Expecting value: line 1 column 1 (char 0)'])

        responses.reset()
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL),
                      json=PAGINATED_AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL),
                      json=AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Collaborator'.format(AIRTABLE_URL),
                      json=AIRTABLE_COLLABORATOR_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()['error'],
            'Found multiple airtable records for sample NA19675 with mismatched values in field dbgap_study_id')
        self.assertEqual(len(responses.calls), 4)
        first_formula = "OR({CollaboratorSampleID}='NA20885',{CollaboratorSampleID}='NA20888')"
        expected_fields = [
            'CollaboratorSampleID', 'Collaborator', 'dbgap_study_id', 'dbgap_subject_id',
            'dbgap_sample_id', 'SequencingProduct', 'dbgap_submission',
        ]
        self.assert_expected_airtable_call(0, first_formula, expected_fields)
        self.assert_expected_airtable_call(1, first_formula, expected_fields, additional_params={'offset': 'abc123'})
        self.assert_expected_airtable_call(2, "OR({CollaboratorSampleID}='NA20889')", expected_fields)
        second_formula = "OR({SeqrCollaboratorSampleID}='NA20888',{SeqrCollaboratorSampleID}='NA20889')"
        expected_fields[0] = 'SeqrCollaboratorSampleID'
        self.assert_expected_airtable_call(3, second_formula, expected_fields)

        # Test success
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        self.assertEqual(len(response_json['rows']), 3)
        expected_samples = {'NA20885', 'NA20888', 'NA20889'}
        self.assertSetEqual({r['sample_id'] for r in response_json['rows']}, expected_samples)
        test_row = next(r for r in response_json['rows'] if r['sample_id'] == 'NA20889')
        self.assertDictEqual(EXPECTED_SAMPLE_METADATA_ROW, test_row)
        self.assertEqual(len(responses.calls), 8)
        self.assert_expected_airtable_call(
            -1, "OR(RECORD_ID()='reca4hcBnbA2cnZf9')", ['CollaboratorID'])
        self.assertSetEqual({call.request.headers['Authorization'] for call in responses.calls}, {'Bearer mock_key'})

        # Test omit airtable columns
        responses.reset()
        response = self.client.get(f'{url}?omitAirtable=true')
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        self.assertEqual(len(response_json['rows']), 3)
        expected_samples = {'NA20885', 'NA20888', 'NA20889'}
        self.assertSetEqual({r['sample_id'] for r in response_json['rows']}, expected_samples)
        test_row = next(r for r in response_json['rows'] if r['sample_id'] == 'NA20889')
        self.assertDictEqual(EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW, test_row)

        # Test empty project
        empty_project_url = reverse(sample_metadata_export, args=['R0002_empty'])
        response = self.client.get(empty_project_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'rows': []})

        # Test all projects
        all_projects_url = reverse(sample_metadata_export, args=['all'])
        response = self.client.get(all_projects_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        self.assertEqual(len(response_json['rows']), 16 + len(self.ADDITIONAL_SAMPLES))
        expected_samples.update({
            'NA19679', 'NA20870', 'HG00732', 'NA20876', 'NA20874', 'NA20875', 'NA19678', 'NA19675', 'HG00731',
            'NA20872', 'NA20881', 'HG00733',
        })
        expected_samples.update(self.ADDITIONAL_SAMPLES)
        self.assertSetEqual({r['sample_id'] for r in response_json['rows']}, expected_samples)
        test_row = next(r for r in response_json['rows'] if r['sample_id'] == 'NA20889')
        self.assertDictEqual(EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW, test_row)
        self.assertEqual(len([r['subject_id'] for r in response_json['rows'] if r['subject_id'] == 'NA20888']), 2)

        self.check_no_analyst_no_access(url)

        # Test non-broad analysts do not have access
        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')


# Tests for AnVIL access disabled
class LocalSummaryDataAPITest(AuthenticationTestCase, SummaryDataAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']
    NUM_MANAGER_SUBMISSIONS = 4
    MANAGER_VARIANT_GUID = 'SV0000006_1248367227_r0004_non'
    ADDITIONAL_SAMPLES = ['NA21234']


def assert_has_expected_calls(self, users, skip_group_call_idxs=None):
    calls = [mock.call(user) for user in users]
    self.mock_list_workspaces.assert_has_calls(calls)
    group_calls = [call for i, call in enumerate(calls) if i in skip_group_call_idxs] if skip_group_call_idxs else calls
    self.mock_get_groups.assert_has_calls(group_calls)
    self.mock_get_ws_acl.assert_not_called()
    self.mock_get_group_members.assert_not_called()


# Test for permissions from AnVIL only
class AnvilSummaryDataAPITest(AnvilAuthenticationTestCase, SummaryDataAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    NUM_MANAGER_SUBMISSIONS = 4
    MANAGER_VARIANT_GUID = 'SV0000006_1248367227_r0004_non'
    ADDITIONAL_SAMPLES = []

    def test_mme_details(self, *args):
        super(AnvilSummaryDataAPITest, self).test_mme_details(*args)
        assert_has_expected_calls(self, [self.no_access_user, self.manager_user, self.analyst_user])
        self.mock_get_ws_access_level.assert_not_called()

    def test_saved_variants_page(self):
        super(AnvilSummaryDataAPITest, self).test_saved_variants_page()
        assert_has_expected_calls(self, [
            self.no_access_user, self.manager_user, self.manager_user, self.analyst_user, self.analyst_user
        ], skip_group_call_idxs=[2])
        self.mock_get_ws_access_level.assert_called_with(
            self.analyst_user, 'my-seqr-billing', 'anvil-1kg project nåme with uniçøde')
