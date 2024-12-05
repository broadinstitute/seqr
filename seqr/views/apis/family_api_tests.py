# -*- coding: utf-8 -*-
import json
import mock
from copy import deepcopy
from datetime import datetime
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls.base import reverse

from matchmaker.models import MatchmakerSubmission
from seqr.views.apis.family_api import update_family_pedigree_image, update_family_assigned_analyst, \
    update_family_fields_handler, update_family_analysed_by, edit_families_handler, delete_families_handler, \
    receive_families_table_handler, create_family_note, update_family_note, delete_family_note, family_page_data, \
    family_variant_tag_summary, update_family_analysis_groups, get_family_rna_seq_data, get_family_phenotype_gene_scores
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, \
    FAMILY_NOTE_FIELDS, FAMILY_FIELDS, IGV_SAMPLE_FIELDS, \
    SAMPLE_FIELDS, INDIVIDUAL_FIELDS, INTERNAL_INDIVIDUAL_FIELDS, INTERNAL_FAMILY_FIELDS, CASE_REVIEW_FAMILY_FIELDS, \
    MATCHMAKER_SUBMISSION_FIELDS, TAG_TYPE_FIELDS, CASE_REVIEW_INDIVIDUAL_FIELDS
from seqr.models import FamilyAnalysedBy, AnalysisGroup

FAMILY_GUID = 'F000001_1'
FAMILY_GUID2 = 'F000002_2'

PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'
PM_REQUIRED_PROJECT_GUID = 'R0003_test'

FAMILY_ID_FIELD = 'familyId'
PREVIOUS_FAMILY_ID_FIELD = 'previousFamilyId'

INDIVIDUAL_GUID = 'I000001_na19675'
INDIVIDUAL2_GUID = 'I000002_na19678'
INDIVIDUAL3_GUID = 'I000003_na19679'

INDIVIDUAL_GUIDS = [INDIVIDUAL_GUID, INDIVIDUAL2_GUID, INDIVIDUAL3_GUID]

SAMPLE_GUIDS = ['S000129_na19675', 'S000130_na19678', 'S000131_na19679']


class FamilyAPITest(object):

    def test_family_page_data(self):
        url = reverse(family_page_data, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {
            'familiesByGuid', 'individualsByGuid', 'familyNotesByGuid', 'samplesByGuid', 'igvSamplesByGuid',
            'mmeSubmissionsByGuid',
        }
        self.assertSetEqual(set(response_json.keys()), response_keys)

        self.assertEqual(len(response_json['familiesByGuid']), 1)
        family = response_json['familiesByGuid'][FAMILY_GUID]
        family_fields = {'individualGuids', 'detailsLoaded', 'postDiscoveryOmimOptions'}
        family_fields.update(FAMILY_FIELDS)
        self.assertSetEqual(set(family.keys()), family_fields)
        self.assertEqual(family['projectGuid'], PROJECT_GUID)
        self.assertSetEqual(set(family['individualGuids']), set(response_json['individualsByGuid'].keys()))
        self.assertListEqual(family['analysedBy'], [
            {'createdBy': 'Test No Access User', 'dataType': 'SNP', 'lastModifiedDate': '2022-07-22T19:27:08.563+00:00'},
        ])
        self.assertListEqual(family['postDiscoveryOmimNumbers'], [615123, 615120])
        self.assertDictEqual(family['postDiscoveryOmimOptions'], {
            '615120': {'phenotypeMimNumber': 615120, 'phenotypes': [{
                'geneSymbol': 'RP11', 'mimNumber': 103320, 'phenotypeMimNumber': 615120,
                'phenotypeDescription': 'Myasthenic syndrome, congenital, 8, with pre- and postsynaptic defects',
                'phenotypeInheritance': 'Autosomal recessive, X-linked recessive', 'chrom': '1', 'start': 29554, 'end': 31109,
            }]}})

        self.assertEqual(len(response_json['individualsByGuid']), 3)
        individual = response_json['individualsByGuid'][INDIVIDUAL_GUID]
        individual_fields = {'sampleGuids', 'igvSampleGuids', 'mmeSubmissionGuid', 'phenotypePrioritizationTools', 'rnaSample'}
        individual_fields.update(INDIVIDUAL_FIELDS)
        self.assertSetEqual(set(individual.keys()), individual_fields)
        self.assertListEqual([
            [
                {'loadedDate': '2024-05-02T06:42:55.397Z', 'tool': 'exomiser'},
                {'loadedDate': '2024-05-02T06:42:55.397Z', 'tool': 'lirical'}
            ], [
                {'loadedDate': '2024-05-02T06:42:55.397Z', 'tool': 'lirical'}
            ], []
        ],
            [response_json['individualsByGuid'][guid].get('phenotypePrioritizationTools') for guid in INDIVIDUAL_GUIDS]
        )
        self.assertListEqual([
            {'loadedDate': '2017-02-05T06:35:55.397Z', 'dataTypes': ['E', 'S', 'T']},
            None,
            {'loadedDate': '2017-02-05T06:14:55.397Z', 'dataTypes': ['S']},
        ],
            [response_json['individualsByGuid'][guid]['rnaSample'] for guid in INDIVIDUAL_GUIDS]
        )
        self.assertSetEqual({PROJECT_GUID}, {i['projectGuid'] for i in response_json['individualsByGuid'].values()})
        self.assertSetEqual({FAMILY_GUID}, {i['familyGuid'] for i in response_json['individualsByGuid'].values()})

        self.assertEqual(len(response_json['samplesByGuid']), 3)
        self.assertSetEqual(set(next(iter(response_json['samplesByGuid'].values())).keys()), SAMPLE_FIELDS)
        self.assertSetEqual({PROJECT_GUID}, {s['projectGuid'] for s in response_json['samplesByGuid'].values()})
        self.assertSetEqual({FAMILY_GUID}, {s['familyGuid'] for s in response_json['samplesByGuid'].values()})
        self.assertEqual(len(individual['sampleGuids']), 1)
        self.assertTrue(set(individual['sampleGuids']).issubset(set(response_json['samplesByGuid'].keys())))

        self.assertEqual(len(response_json['igvSamplesByGuid']), 1)
        self.assertSetEqual(set(next(iter(response_json['igvSamplesByGuid'].values())).keys()), IGV_SAMPLE_FIELDS)
        self.assertSetEqual({PROJECT_GUID}, {s['projectGuid'] for s in response_json['igvSamplesByGuid'].values()})
        self.assertSetEqual({FAMILY_GUID}, {s['familyGuid'] for s in response_json['igvSamplesByGuid'].values()})
        self.assertSetEqual({INDIVIDUAL_GUID}, {s['individualGuid'] for s in response_json['igvSamplesByGuid'].values()})
        self.assertSetEqual(set(individual['igvSampleGuids']), set(response_json['igvSamplesByGuid'].keys()))

        self.assertEqual(len(response_json['mmeSubmissionsByGuid']), 1)
        submission = next(iter(response_json['mmeSubmissionsByGuid'].values()))
        self.assertSetEqual(set(submission.keys()), MATCHMAKER_SUBMISSION_FIELDS)
        self.assertEqual(submission['individualGuid'], INDIVIDUAL_GUID)
        self.assertEqual(submission['submissionGuid'], individual['mmeSubmissionGuid'])

        self.assertEqual(len(response_json['familyNotesByGuid']), 3)
        self.assertSetEqual(set(next(iter(response_json['familyNotesByGuid'].values())).keys()), FAMILY_NOTE_FIELDS)
        self.assertSetEqual({FAMILY_GUID}, {f['familyGuid'] for f in response_json['familyNotesByGuid'].values()})

        # Test discovery omim options
        discovery_omim_url = reverse(family_page_data, args=['F000012_12'])
        response = self.client.get(discovery_omim_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertSetEqual(set(response_json['familiesByGuid'].keys()), {'F000012_12'})
        self.assertListEqual(response_json['familiesByGuid']['F000012_12']['postDiscoveryOmimNumbers'], [616126])
        self.assertDictEqual(response_json['familiesByGuid']['F000012_12']['postDiscoveryOmimOptions'], {'616126': {
            'phenotypeMimNumber': 616126, 'phenotypes': [{
                'chrom': '1',
                'start': 11869,
                'end': 14409,
                'geneSymbol': 'OR4G11P',
                'mimNumber': 147571,
                'phenotypeMimNumber': 616126,
                'phenotypeDescription': 'Immunodeficiency 38',
                'phenotypeInheritance': 'Autosomal recessive',
            }]}, '615120': {
            'phenotypeMimNumber': 615120, 'phenotypes': [{
                'chrom': '1',
                'start': 29554,
                'end': 31109,
                'geneSymbol': 'RP11',
                'mimNumber': 103320,
                'phenotypeDescription': 'Myasthenic syndrome, congenital, 8, with pre- and postsynaptic defects',
                'phenotypeInheritance': 'Autosomal recessive, X-linked recessive',
                'phenotypeMimNumber': 615120,
            }, {
                'chrom': '1',
                'start': 249044482,
                'end': 249055991,
                'geneSymbol': None,
                'mimNumber': 600315,
                'phenotypeDescription': '?Immunodeficiency 16', 'phenotypeInheritance': 'Autosomal recessive',
                'phenotypeMimNumber': 615120,
            }]}})

        # Test analyst users have internal fields returned
        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        family_fields.update(CASE_REVIEW_FAMILY_FIELDS)
        internal_family_fields = deepcopy(family_fields)
        internal_family_fields.update(INTERNAL_FAMILY_FIELDS)
        individual_fields.update(CASE_REVIEW_INDIVIDUAL_FIELDS)
        internal_individual_fields = deepcopy(individual_fields)
        internal_individual_fields.update(INTERNAL_INDIVIDUAL_FIELDS)
        self.assertSetEqual(set(response_json['familiesByGuid'][FAMILY_GUID].keys()), internal_family_fields)
        self.assertSetEqual(set(next(iter(response_json['individualsByGuid'].values())).keys()), internal_individual_fields)

        self.mock_analyst_group.__str__.return_value = ''
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json['familiesByGuid'][FAMILY_GUID].keys()), family_fields)
        self.assertSetEqual(set(next(iter(response_json['individualsByGuid'].values())).keys()), individual_fields)

        # Test invalid family guid
        response = self.client.get(url.replace(FAMILY_GUID, 'invalid_guid'))
        self.assertEqual(response.status_code, 404)

    def test_family_variant_tag_summary(self):
        url = reverse(family_variant_tag_summary, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {
            'projectsByGuid', 'familiesByGuid', 'familyTagTypeCounts', 'genesById',
        }
        self.assertSetEqual(set(response_json.keys()), response_keys)

        family = response_json['familiesByGuid'][FAMILY_GUID]
        self.assertSetEqual(set(family.keys()), {'familyGuid', 'discoveryTags'})
        self.assertSetEqual({tag['variantGuid'] for tag in family['discoveryTags']}, {'SV0000001_2103343353_r0390_100'})

        project = response_json['projectsByGuid'][PROJECT_GUID]
        self.assertSetEqual(set(project.keys()), {'variantTagTypes', 'variantFunctionalTagTypes'})
        self.assertSetEqual(set(project['variantTagTypes'][0].keys()), TAG_TYPE_FIELDS)

        self.assertDictEqual(response_json['familyTagTypeCounts'], {
            FAMILY_GUID: {'Review': 1, 'Tier 1 - Novel gene and phenotype': 1, 'MME Submission': 1},
        })
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000135953'})

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    def test_edit_families_handler(self, mock_pm_group):
        url = reverse(edit_families_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

        # send invalid request
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, "'families' not specified")

        response = self.client.post(url, content_type='application/json', data=json.dumps({'families': [
            {'familyGuid': FAMILY_GUID, 'familyId': '2', 'description': 'Test description 1'}
        ]}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'], 'Cannot update the following family ID(s) as they are already in use: 1 -> 2')

        # send request with a "families" attribute
        req_values = {
            'families': [
                {'familyGuid': FAMILY_GUID, 'description': 'Test description 1'},
                {'familyGuid': FAMILY_GUID2, PREVIOUS_FAMILY_ID_FIELD: '2', FAMILY_ID_FIELD: '22', 'description': 'Test description 2'},
            ]
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), ['familiesByGuid'])
        self.assertEqual(response_json['familiesByGuid'][FAMILY_GUID]['description'], 'Test description 1')
        self.assertEqual(response_json['familiesByGuid']['F000002_2'][FAMILY_ID_FIELD], '22')
        self.assertEqual(response_json['familiesByGuid']['F000002_2']['description'], 'Test description 2')
        self.assertSetEqual(set(response_json['familiesByGuid'].keys()), set([FAMILY_GUID, 'F000002_2']))

        # Test PM permission
        url = reverse(edit_families_handler, args=[PM_REQUIRED_PROJECT_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'
        mock_pm_group.__eq__.side_effect = lambda s: s == 'project-managers'

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'families': [{'familyGuid': 'F000012_12'}]}))
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    def test_delete_families_handler(self, mock_pm_group):
        url = reverse(delete_families_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

        # Test errors
        response = self.client.post(url, content_type='application/json', data=json.dumps({'families': None}))
        self.assertEqual(response.status_code, 400)

        req_values = {
            'families': [
                {'familyGuid': FAMILY_GUID},
                {'familyGuid': FAMILY_GUID2}
            ]
        }
        response = self.client.post(url, content_type='application/json', data=json.dumps(req_values))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Unable to delete individuals with active MME submission: NA19675_1'])

        with mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', ''):
            response = self.client.post(url, content_type='application/json', data=json.dumps(req_values))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Unable to delete individuals with active MME submission: NA19675_1',
            'Unable to delete individuals with active search sample: HG00731, HG00732, HG00733, NA19675_1, NA19678',
        ])

        # Test success
        MatchmakerSubmission.objects.update(deleted_date=datetime.now())

        response = self.client.post(url, content_type='application/json', data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'individualsByGuid', 'familiesByGuid'})
        self.assertIsNone(response_json['familiesByGuid'][FAMILY_GUID])
        self.assertIsNone(response_json['familiesByGuid'][FAMILY_GUID2])
        self.assertEqual(FamilyAnalysedBy.objects.count(), 0)

        # Test PM permission
        url = reverse(delete_families_handler, args=[PM_REQUIRED_PROJECT_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'
        mock_pm_group.__eq__.side_effect = lambda s: s == 'project-managers'

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'families': [{'familyGuid': 'F000012_12'}]}))
        self.assertEqual(response.status_code, 200)

    def test_update_family_analysed_by(self):
        url = reverse(update_family_analysed_by, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        # send request
        response = self.client.post(url, content_type='application/json', data=json.dumps({'dataType': 'SV'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertEqual(len(response_json[FAMILY_GUID]['analysedBy']), 2)
        self.assertEqual(response_json[FAMILY_GUID]['analysedBy'][1]['createdBy'], 'Test Collaborator User')
        self.assertEqual(response_json[FAMILY_GUID]['analysedBy'][1]['dataType'], 'SV')

    def test_update_family_analysis_groups(self):
        url = reverse(update_family_analysis_groups, args=[FAMILY_GUID])
        self.check_manager_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'analysisGroups': [
            {'analysisGroupGuid': 'AG0000185_accepted', 'name': 'Accepted'}]}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), ['analysisGroupsByGuid'])
        self.assertSetEqual(set(response_json['analysisGroupsByGuid'].keys()), {'AG0000183_test_group', 'AG0000185_accepted'})
        self.assertTrue(FAMILY_GUID in response_json['analysisGroupsByGuid']['AG0000185_accepted']['familyGuids'])
        self.assertFalse(FAMILY_GUID in response_json['analysisGroupsByGuid']['AG0000183_test_group']['familyGuids'])

        self.assertIsNotNone(AnalysisGroup.objects.get(guid='AG0000185_accepted').families.filter(guid=FAMILY_GUID).first())
        self.assertIsNone(AnalysisGroup.objects.get(guid='AG0000183_test_group').families.filter(guid=FAMILY_GUID).first())

    def test_update_family_pedigree_image(self):
        url = reverse(update_family_pedigree_image, args=[FAMILY_GUID])
        self.check_manager_login(url)

        f = SimpleUploadedFile("new_ped_image_123.png", b"file_content")

        # send invalid request
        response = self.client.post(url, {'f1': f, 'f2': f})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Received 2 files')

        # send valid add/update request
        response = self.client.post(url, {'f': f})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertRegex(response_json[FAMILY_GUID]['pedigreeImage'], '/media/pedigree_images/new_ped_image_.+\.png')

        # send valid delete request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertIsNone(response_json[FAMILY_GUID]['pedigreeImage'])

    def test_update_family_assigned_analyst(self):
        url = reverse(update_family_assigned_analyst, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        # send invalid username (without permission)
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'assigned_analyst_username': 'invalid_username'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'specified user does not exist')

        # send valid request
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'assigned_analyst_username': 'test_user'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['assignedAnalyst']['email'], 'test_user@broadinstitute.org')
        self.assertEqual(response_json[FAMILY_GUID]['assignedAnalyst']['fullName'], 'Test User')

        # unassign analyst
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertIsNone(response_json[FAMILY_GUID]['assignedAnalyst'])

    def test_update_success_story_types(self):
        url = reverse(update_family_fields_handler, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'successStoryTypes': ['O', 'D']}))
        self.assertEqual(response.status_code, 403)

        self.login_analyst_user()
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'successStoryTypes': ['O', 'D']}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json[FAMILY_GUID]['successStoryTypes'], ['O', 'D'])

        self.check_no_analyst_no_access(url, get_response=lambda: self.client.post(
            url, content_type='application/json', data=json.dumps({'successStoryTypes': []})))

    @mock.patch('seqr.views.utils.json_to_orm_utils.timezone.now', lambda: datetime.strptime('2020-01-01', '%Y-%m-%d'))
    def test_update_family_fields(self):
        url = reverse(update_family_fields_handler, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        body = {FAMILY_ID_FIELD: 'new_id', 'description': 'Updated description', 'analysis_status': 'C'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json[FAMILY_GUID]['description'], 'Updated description')
        self.assertEqual(response_json[FAMILY_GUID][FAMILY_ID_FIELD], '1')
        self.assertEqual(response_json[FAMILY_GUID]['displayName'], '1')
        self.assertEqual(response_json[FAMILY_GUID]['analysisStatus'], 'C')
        self.assertEqual(response_json[FAMILY_GUID]['analysisStatusLastModifiedBy'], 'Test Collaborator User')
        self.assertEqual(response_json[FAMILY_GUID]['analysisStatusLastModifiedDate'], '2020-01-01T00:00:00')

        # Do not update audit fields if value does not change
        self.login_manager()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[FAMILY_GUID]['analysisStatusLastModifiedBy'], 'Test Collaborator User')

        # Test External AnVIL projects
        external_family_url = reverse(update_family_fields_handler, args=['F000014_14'])
        response = self.client.post(external_family_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json['F000014_14']['description'], 'Updated description')
        expected_id = 'new_id' if self._anvil_enabled() else '14'
        self.assertEqual(response_json['F000014_14'][FAMILY_ID_FIELD], expected_id)
        self.assertEqual(response_json['F000014_14']['displayName'], expected_id)

    def _anvil_enabled(self):
        return not self.ES_HOSTNAME

    @mock.patch('seqr.views.utils.file_utils.anvil_enabled', lambda: False)
    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    def test_receive_families_table_handler(self, mock_pm_group):
        url = reverse(receive_families_table_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

        # send invalid request
        data = b'Description	Coded Phenotype\n\
        "family one description"	""\n\
        "family two description"	""'
        response = self.client.post(url, {'f': SimpleUploadedFile("1000_genomes demo_families.tsv", data)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid header, missing family id column')
        self.assertDictEqual(response.json(), {
            'errors': ['Invalid header, missing family id column'], 'warnings': []})

        data = b'Family ID	Previous Family ID	Display Name	Description	Coded Phenotype\n\
        "1_renamed"	"1_old"	"1"	"family one description"	""\n\
        "22"	""	"2"	"family two description"	""'
        response = self.client.post(url, {'f': SimpleUploadedFile("1000_genomes demo_families.tsv", data)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid input')
        self.assertDictEqual(response.json(), {
            'errors': ['Could not find families with the following previous IDs: 1_old',
                       'Could not find families with the following current IDs: 22'], 'warnings': []})

        # send valid request
        data = b'Family ID	Previous Family ID	Display Name	Description	Phenotype Description	MONDO ID\n\
"1_renamed"	"1"	"1"	"family one description"	"dystrophy"	"MONDO:12345"\n\
"2"	""	"2"	"family two description"	""	""'

        response = self.client.post(url, {'f': SimpleUploadedFile("1000_genomes demo_families.tsv", data)})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings', 'uploadedFileId'})

        edit_url = reverse(edit_families_handler, args=[PROJECT_GUID])

        response = self.client.post(edit_url, content_type='application/json',
                data=json.dumps({'uploadedFileId': response_json['uploadedFileId']}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), ['familiesByGuid'])
        self.assertSetEqual(set(response_json['familiesByGuid'].keys()), {FAMILY_GUID2, FAMILY_GUID})
        family_1 = response_json['familiesByGuid'][FAMILY_GUID]
        self.assertEqual(family_1['description'], 'family one description')
        self.assertEqual(family_1['familyId'], '1_renamed')
        self.assertEqual(family_1['codedPhenotype'], 'dystrophy')
        self.assertEqual(family_1['mondoId'], 'MONDO:12345')
        family_2 = response_json['familiesByGuid'][FAMILY_GUID2]
        self.assertEqual(family_2['description'], 'family two description')
        self.assertEqual(family_2['familyId'], '2')

        internal_field_data = b'Family ID	External Data\n\
"3"	""\n\
"2"	"ONT lrGS; BioNano"'
        response = self.client.post(url,  {'f': SimpleUploadedFile('families.tsv', internal_field_data)})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            edit_url, content_type='application/json', data=json.dumps({'uploadedFileId': response.json()['uploadedFileId']}))
        self.assertEqual(response.status_code, 403)

        # Test PM permission
        url = reverse(receive_families_table_handler, args=[PM_REQUIRED_PROJECT_GUID])
        edit_url = reverse(edit_families_handler, args=[PM_REQUIRED_PROJECT_GUID])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'
        mock_pm_group.__eq__.side_effect = lambda s: s == 'project-managers'

        internal_field_data = internal_field_data.replace(b'3', b'11').replace(b'2', b'12')
        response = self.client.post(url,  {'f': SimpleUploadedFile('families.tsv', internal_field_data)})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            edit_url, content_type='application/json', data=json.dumps({'uploadedFileId': response.json()['uploadedFileId']}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json['familiesByGuid']['F000011_11']['externalData'], [])
        self.assertListEqual(response_json['familiesByGuid']['F000012_12']['externalData'], ['L', 'B'])

    def test_create_update_and_delete_family_note(self):
        # create the note
        create_note_url = reverse(create_family_note, args=[FAMILY_GUID])
        self.check_collaborator_login(create_note_url)

        response = self.client.post(create_note_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Missing required field(s): note, noteType'})

        response = self.client.post(create_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new analysis note', 'noteType': 'A'}
        ))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'familyNotesByGuid'})
        self.assertEqual(len(response_json['familyNotesByGuid']), 1)
        new_note_guid = list(response_json['familyNotesByGuid'].keys())[0]
        new_note_response = list(response_json['familyNotesByGuid'].values())[0]
        self.assertSetEqual(set(new_note_response.keys()), FAMILY_NOTE_FIELDS)
        self.assertEqual(new_note_response['noteGuid'], new_note_guid)
        self.assertEqual(new_note_response['note'], 'new analysis note')
        self.assertEqual(new_note_response['noteType'], 'A')
        self.assertEqual(new_note_response['createdBy'], 'Test Collaborator User')

        # update the note
        update_note_url = reverse(update_family_note, args=[FAMILY_GUID, new_note_guid])
        response = self.client.post(update_note_url, content_type='application/json',  data=json.dumps(
            {'note': 'updated note'}))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json, {'familyNotesByGuid': {new_note_guid: mock.ANY}})
        updated_note_response = response_json['familyNotesByGuid'][new_note_guid]
        self.assertEqual(updated_note_response['note'], 'updated note')

        # test other users cannot modify the note
        self.login_manager()
        response = self.client.post(update_note_url, content_type='application/json', data=json.dumps(
            {'note': 'further updated note'}))
        self.assertEqual(response.status_code, 403)

        # delete the gene_note
        delete_note_url = reverse(delete_family_note, args=[FAMILY_GUID, new_note_guid])

        response = self.client.post(delete_note_url, content_type='application/json')
        self.assertEqual(response.status_code, 403)

        self.login_collaborator()
        response = self.client.post(delete_note_url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'familyNotesByGuid': {new_note_guid: None}})

    def test_get_family_rna_seq_data(self):
        url = reverse(get_family_rna_seq_data, args=[FAMILY_GUID, 'ENSG00000135953'])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'F': {'individualData': {'NA19675_1': 1.01}, 'rdgData': [1.01]},
            'M': {'individualData': {'NA19675_1': 8.38}, 'rdgData': [8.38]}
        })

    def test_get_family_phenotype_gene_scores(self):
        url = reverse(get_family_phenotype_gene_scores, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'genesById': {
                'ENSG00000268903': {
                    'chromGrch37': '1', 'chromGrch38': '1', 'clinGen': None, 'cnSensitivity': {},
                    'codingRegionSizeGrch37': 0, 'codingRegionSizeGrch38': 0, 'constraints': {},
                    'endGrch37': 135895, 'endGrch38': 135895, 'genCc': {}, 'sHet': {},
                    'gencodeGeneType': 'processed_pseudogene', 'geneId': 'ENSG00000268903',
                    'geneSymbol': 'AL627309.7', 'mimNumber': None, 'omimPhenotypes': [],
                    'startGrch37': 135141, 'startGrch38': 135141
                }
            },
            'phenotypeGeneScores': {
                'I000001_na19675': {
                    'ENSG00000268903': {
                        'exomiser': [
                            {'diseaseId': 'OMIM:219800', 'diseaseName': 'Cystinosis, nephropathic', 'rank': 2,
                             'scores': {'exomiser_score': 0.969347946, 'phenotype_score': 0.443567539,
                                        'variant_score': 0.999200702}},
                            {'diseaseId': 'OMIM:618460', 'diseaseName': 'Khan-Khan-Katsanis syndrome', 'rank': 1,
                             'scores': {'exomiser_score': 0.977923765, 'phenotype_score': 0.603998205,
                                        'variant_score': 1}}
                        ]
                    }
                },
                'I000002_na19678': {
                    'ENSG00000268903': {
                        'lirical': [
                            {'diseaseId': 'OMIM:219800', 'diseaseName': 'Cystinosis, nephropathic', 'rank': 1,
                             'scores': {'compositeLR': 0.003, 'post_test_probability': 0}
                            }
                        ]
                    }
                }
            }
        })


class LocalFamilyAPITest(AuthenticationTestCase, FamilyAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']


class AnvilFamilyAPITest(AnvilAuthenticationTestCase, FamilyAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']
