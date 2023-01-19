# -*- coding: utf-8 -*-
import json
import mock

from copy import deepcopy
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls.base import reverse

from seqr.models import Individual
from seqr.views.apis.individual_api import edit_individuals_handler, update_individual_handler, \
    delete_individuals_handler, receive_individuals_table_handler, save_individuals_table_handler, \
    receive_individuals_metadata_handler, save_individuals_metadata_table_handler, update_individual_hpo_terms, \
    get_hpo_terms, get_individual_rna_seq_data
from seqr.views.utils.test_utils import AuthenticationTestCase, INDIVIDUAL_FIELDS, INDIVIDUAL_CORE_FIELDS, \
    CORE_INTERNAL_INDIVIDUAL_FIELDS

PROJECT_GUID = 'R0001_1kg'
PM_REQUIRED_PROJECT_GUID = 'R0003_test'

INDIVIDUAL_GUID = "I000001_na19675"
ID_UPDATE_GUID = "I000002_na19678"
UPDATED_ID = "NA19678_1"
UPDATED_MATERNAL_ID = "NA20870"

INDIVIDUAL_IDS_UPDATE_DATA = {
    'individualGuid': ID_UPDATE_GUID,
    'familyId': '1',
    'individualId': UPDATED_ID,
    'maternalId': UPDATED_MATERNAL_ID,
    'paternalId': '',
    'sex': 'M',
    'notes': '',
    'population': None,
    'filterFlags': None,
    'projectGuid': PROJECT_GUID,
}

INDIVIDUAL_UPDATE_GUID = "I000007_na20870"
INDIVIDUAL_UPDATE_DATA = {
    'displayName': 'NA20870',
    'notes': 'A note',
    'birthYear': 2000,
    'features': [{
        'id': 'HP:0002011',
        'label': 'nervous system abnormality',
        'category': 'HP:0000708',
        'categoryName': 'Nervous',
        'qualifiers': [{'type': 'onset', 'label': 'congenital'}],
    }, {
        'id': 'HP:0011675',
        'notes': 'A new term',
    }],
    'absentFeatures': [],
    'absentNonstandardFeatures': [{'id': 'Some new feature', 'notes': 'No term for this', 'details': 'extra detail'}]
}

PM_REQUIRED_INDIVIDUAL_GUID = 'I000017_na20889'
PM_REQUIRED_INDIVIDUAL_UPDATE_DATA = {
    'individualGuid': PM_REQUIRED_INDIVIDUAL_GUID, 'individualId': 'NA20889', 'familyId': '12', 'displayName': 'NA20889_a'
}

FAMILY_UPDATE_GUID = "I000007_na20870"
INDIVIDUAL_FAMILY_UPDATE_DATA = {
    "individualGuid": FAMILY_UPDATE_GUID,
    "familyId": "1",
    "individualId": UPDATED_MATERNAL_ID,
}

@mock.patch('seqr.utils.middleware.DEBUG', False)
class IndividualAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    def test_update_individual_handler(self):
        edit_individuals_url = reverse(update_individual_handler, args=[INDIVIDUAL_UPDATE_GUID])
        self.check_collaborator_login(edit_individuals_url)

        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps(INDIVIDUAL_UPDATE_DATA))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), [INDIVIDUAL_UPDATE_GUID])
        self.assertSetEqual(set(response_json[INDIVIDUAL_UPDATE_GUID].keys()), INDIVIDUAL_CORE_FIELDS)
        individual = Individual.objects.get(guid=INDIVIDUAL_UPDATE_GUID)
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['displayName'], 'NA20870')
        self.assertEqual(individual.display_name, '')
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['notes'], 'A note')
        self.assertIsNone(response_json[INDIVIDUAL_UPDATE_GUID]['birthYear'])
        self.assertFalse('features' in response_json[INDIVIDUAL_UPDATE_GUID])
        self.assertIsNone(individual.features)

        self.login_manager()
        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps(INDIVIDUAL_UPDATE_DATA))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json[INDIVIDUAL_UPDATE_GUID].keys()), INDIVIDUAL_CORE_FIELDS)
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['birthYear'], 2000)

        update_json = {'analyteType': 'D', 'tissueAffectedStatus': False}
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps(update_json))
        self.assertEqual(response.status_code, 403)

        self.login_analyst_user()
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps(update_json))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        response_fields = deepcopy(INDIVIDUAL_CORE_FIELDS)
        response_fields.update(CORE_INTERNAL_INDIVIDUAL_FIELDS)
        self.assertSetEqual(set(response_json[INDIVIDUAL_UPDATE_GUID].keys()), response_fields)
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['analyteType'], 'D')
        self.assertFalse(response_json[INDIVIDUAL_UPDATE_GUID]['tissueAffectedStatus'])

    def test_update_individual_hpo_terms(self):
        edit_individuals_url = reverse(update_individual_hpo_terms, args=[INDIVIDUAL_UPDATE_GUID])
        self.check_manager_login(edit_individuals_url)

        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps(INDIVIDUAL_UPDATE_DATA))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), [INDIVIDUAL_UPDATE_GUID])
        self.assertListEqual(response_json[INDIVIDUAL_UPDATE_GUID]['features'], [
            {
                'id': 'HP:0002011',
                'category': 'HP:0000707',
                'label': 'Morphological abnormality of the central nervous system',
                'qualifiers': [{'type': 'onset', 'label': 'congenital'}],
            },
            {'id': 'HP:0011675', 'category': 'HP:0001626', 'label': 'Arrhythmia', 'notes': 'A new term'},
        ])
        self.assertListEqual(response_json[INDIVIDUAL_UPDATE_GUID]['absentNonstandardFeatures'], [
            {'id': 'Some new feature', 'notes': 'No term for this'}
        ])
        self.assertIsNone(response_json[INDIVIDUAL_UPDATE_GUID]['absentFeatures'])
        self.assertIsNone(response_json[INDIVIDUAL_UPDATE_GUID]['nonstandardFeatures'])

        self.assertListEqual(Individual.objects.get(guid=INDIVIDUAL_UPDATE_GUID).features, [
            {'id': 'HP:0002011', 'qualifiers': [{'type': 'onset', 'label': 'congenital'}]},
            {'id': 'HP:0011675', 'notes': 'A new term'},
        ])

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    def test_edit_individuals(self, mock_pm_group):
        edit_individuals_url = reverse(edit_individuals_handler, args=[PROJECT_GUID])
        self.check_manager_login(edit_individuals_url)

        # send invalid requests
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, "'individuals' not specified")

        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            "NA20870 is the mother of NA19678_1 but is not included. Make sure to create an additional record with NA20870 as the Individual ID",
        ])

        # send valid request
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA, INDIVIDUAL_FAMILY_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'individualsByGuid', 'familiesByGuid'})
        self.assertSetEqual({'F000001_1', 'F000003_3'}, set(response_json['familiesByGuid']))
        self.assertSetEqual({ID_UPDATE_GUID, FAMILY_UPDATE_GUID, INDIVIDUAL_GUID, "I000003_na19679"},
                            set(response_json['familiesByGuid']['F000001_1']['individualGuids']))
        self.assertListEqual(response_json['familiesByGuid']['F000003_3']['individualGuids'], [])
        self.assertIsNone(response_json['familiesByGuid']['F000001_1']['pedigreeImage'])
        self.assertIsNone(response_json['familiesByGuid']['F000003_3']['pedigreeImage'])

        self.assertSetEqual({ID_UPDATE_GUID, FAMILY_UPDATE_GUID, INDIVIDUAL_GUID},
                            set(response_json['individualsByGuid']))
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['individualId'], UPDATED_ID)
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['maternalId'], UPDATED_MATERNAL_ID)
        self.assertEqual(response_json['individualsByGuid'][INDIVIDUAL_GUID]['paternalId'], UPDATED_ID)

        # test only updating parental IDs
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [{
                'individualGuid': ID_UPDATE_GUID,
                'familyId': '1',
                'individualId': UPDATED_ID,
                'maternalId': 'NA19679',
            }]
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'individualsByGuid', 'familiesByGuid'})
        self.assertDictEqual({}, response_json['familiesByGuid'])
        self.assertSetEqual({ID_UPDATE_GUID}, set(response_json['individualsByGuid']))
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['individualId'], UPDATED_ID)
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['maternalId'], 'NA19679')

        # Test PM permission
        pm_required_edit_individuals_url = reverse(edit_individuals_handler, args=[PM_REQUIRED_PROJECT_GUID])
        response = self.client.post(pm_required_edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [PM_REQUIRED_INDIVIDUAL_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.post(pm_required_edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [PM_REQUIRED_INDIVIDUAL_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 403)

        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'
        response = self.client.post(pm_required_edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [PM_REQUIRED_INDIVIDUAL_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'individualsByGuid': {PM_REQUIRED_INDIVIDUAL_GUID: mock.ANY},
            'familiesByGuid': {}
        })

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    def test_delete_individuals(self, mock_pm_group):
        individuals_url = reverse(delete_individuals_handler, args=[PROJECT_GUID])
        self.check_manager_login(individuals_url)

        # send invalid requests
        response = self.client.post(individuals_url, content_type='application/json', data=json.dumps({
            'individualsX': [INDIVIDUAL_IDS_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 400)

        # send valid requests
        response = self.client.post(individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'individualsByGuid', 'familiesByGuid'})
        self.assertDictEqual(response_json, {
            'individualsByGuid': {'I000002_na19678': None},
            'familiesByGuid': {'F000001_1': mock.ANY}
        })
        self.assertFalse('I000002_na19678' in response_json['familiesByGuid']['F000001_1']['individualGuids'])
        self.assertIsNone(response_json['familiesByGuid']['F000001_1']['pedigreeImage'])

        # Test PM permission
        pm_required_delete_individuals_url = reverse(delete_individuals_handler, args=[PM_REQUIRED_PROJECT_GUID])
        response = self.client.post(
            pm_required_delete_individuals_url, content_type='application/json', data=json.dumps({
                'individuals': [PM_REQUIRED_INDIVIDUAL_UPDATE_DATA]
            }))
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.post(
            pm_required_delete_individuals_url, content_type='application/json', data=json.dumps({
                'individuals': [PM_REQUIRED_INDIVIDUAL_UPDATE_DATA]
            }))
        self.assertEqual(response.status_code, 403)

        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'
        response = self.client.post(
            pm_required_delete_individuals_url, content_type='application/json', data=json.dumps({
                'individuals': [PM_REQUIRED_INDIVIDUAL_UPDATE_DATA]
            }))

        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Unable to delete individuals with active MME submission: NA20889'])

        response = self.client.post(
            pm_required_delete_individuals_url, content_type='application/json', data=json.dumps({
                'individuals': [{'individualGuid': 'I000015_na20885'}]
            }))

        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    def test_individuals_table_handler(self):
        individuals_url = reverse(receive_individuals_table_handler, args=[PROJECT_GUID])
        self.check_manager_login(individuals_url)

        # send invalid requests
        response = self.client.get(individuals_url)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Received 0 files instead of 1'], 'warnings': []})

        response = self.client.post(individuals_url, {'f': SimpleUploadedFile('test.tsv', 'family   indiv\n1    '.encode('utf-8'))})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': mock.ANY, 'warnings': []})
        errors = response.json()['errors']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0], "Error while converting test.tsv rows to json: Individual Id not specified in row #1")

        response = self.client.post(individuals_url, {'f': SimpleUploadedFile(
            'test.tsv', 'Family ID	Individual ID	Previous Individual ID\n"1"	"NA19675_1"	"NA19675"'.encode('utf-8'))})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': ['Could not find individuals with the following previous IDs: NA19675'], 'warnings': []
        })

        response = self.client.post(individuals_url, {'f': SimpleUploadedFile(
            'test.tsv', 'Family ID	Individual ID	Paternal ID\n"1"	"NA19675_1"	"NA19678_dad"'.encode('utf-8'))})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': [
                "NA19678_dad is the father of NA19675_1 but is not included. Make sure to create an additional record with NA19678_dad as the Individual ID",
            ],
            'warnings': [],
        })

        # send valid requests
        data = 'Family ID	Individual ID	Previous Individual ID	Paternal ID	Maternal ID	Sex	Affected Status	Notes	familyNotes\n\
"1"	"NA19675"	"NA19675_1"	"NA19678"	"NA19679"	"Female"	"Affected"	"A affected individual, test1-zsf"	""\n\
"1"	"NA19678"	""	""	""	"Male"	"Unaffected"	"a individual note"	""\n\
"1"	"NA19678"	""	""	""	"Male"	"Unaffected"	"a individual note"	""\n\
"21"	"HG00735"	""	""	""	"Female"	"Unaffected"	""	"a new family""\n\
"21"	"HG00735"	""	""	""	"Female"	"Unaffected"	""	""'

        f = SimpleUploadedFile("1000_genomes demo_individuals.tsv", data.encode('utf-8'))

        response = self.client.post(individuals_url, {'f': f})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings', 'uploadedFileId'})
        self.assertListEqual(response_json['errors'], [])
        self.assertListEqual(response_json['warnings'], [])
        self.assertListEqual(response_json['info'], [
            '2 families, 3 individuals parsed from 1000_genomes demo_individuals.tsv',
            '1 new families, 1 new individuals will be added to the project',
            '2 existing individuals will be updated',
        ])

        url = reverse(save_individuals_table_handler, args=[PROJECT_GUID, response_json['uploadedFileId']])

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'individualsByGuid', 'familiesByGuid', 'familyNotesByGuid'})

        self.assertEqual(len(response_json['familiesByGuid']), 2)
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        new_family_guid = next(guid for guid in response_json['familiesByGuid'].keys() if guid != 'F000001_1')
        self.assertEqual(response_json['familiesByGuid'][new_family_guid]['familyId'], '21')
        self.assertIsNone(response_json['familiesByGuid']['F000001_1']['pedigreeImage'])

        self.assertEqual(len(response_json['familyNotesByGuid']), 1)
        new_note = list(response_json['familyNotesByGuid'].values())[0]
        self.assertEqual(new_note['note'], 'a new family')
        self.assertEqual(new_note['noteType'], 'C')
        self.assertEqual(new_note['createdBy'], 'Test Manager User')

        self.assertEqual(len(response_json['individualsByGuid']), 3)
        self.assertTrue('I000001_na19675' in response_json['individualsByGuid'])
        self.assertTrue('I000002_na19678' in response_json['individualsByGuid'])
        new_indiv_guid = next(guid for guid in response_json['individualsByGuid'].keys()
                              if guid not in {'I000001_na19675', 'I000002_na19678'})
        self.assertEqual(response_json['individualsByGuid']['I000001_na19675']['individualId'], 'NA19675')
        self.assertEqual(response_json['individualsByGuid']['I000001_na19675']['sex'], 'F')
        self.assertEqual(
            response_json['individualsByGuid']['I000001_na19675']['notes'], 'A affected individual, test1-zsf')
        self.assertEqual(response_json['individualsByGuid'][new_indiv_guid]['individualId'], 'HG00735')
        self.assertEqual(response_json['individualsByGuid'][new_indiv_guid]['sex'], 'F')

        # Test PM permission
        receive_url = reverse(receive_individuals_table_handler, args=[PM_REQUIRED_PROJECT_GUID])
        save_url = reverse(save_individuals_table_handler, args=[PM_REQUIRED_PROJECT_GUID, '123'])
        response = self.client.post(receive_url, {'f': f})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(save_url)
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.post(receive_url, {
            'f': SimpleUploadedFile('individuals.tsv', 'Family ID	Individual ID\n1	2'.encode('utf-8'))})
        self.assertEqual(response.status_code, 200)
        save_url = reverse(save_individuals_table_handler, args=[
            PM_REQUIRED_PROJECT_GUID, response.json()['uploadedFileId']])
        response = self.client.post(save_url)
        self.assertEqual(response.status_code, 200)


    def _is_expected_individuals_metadata_upload(self, response, expected_families=False):
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        expected_response = {
            'uploadedFileId': mock.ANY,
            'errors': [],
            'warnings': [
                "The following HPO terms were not found in seqr's HPO data and will not be added: HP:0004322 (NA19675_1); HP:0100258 (NA19679)",
                'Unable to find matching ids for 1 individuals. The following entries will not be updated: HG00731',
                'No changes detected for 2 individuals. The following entries will not be updated: NA19678, NA19679',
            ],
            'info': ['1 individuals will be updated'],
        }
        if expected_families:
            expected_response['warnings'].insert(1, 'The following invalid values for "assigned_analyst" will not be added: test_user_no_access@test.com (NA19679)')
        self.assertDictEqual(response_json, expected_response)

        # Save uploaded file
        url = reverse(save_individuals_metadata_table_handler, args=[PROJECT_GUID, response_json['uploadedFileId']])

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        expected_keys = {'individualsByGuid'}
        if expected_families:
            expected_keys.add('familiesByGuid')
        self.assertSetEqual(set(response_json.keys()), expected_keys)
        self.assertListEqual(list(response_json['individualsByGuid'].keys()), ['I000001_na19675'])
        self.assertSetEqual(set(response_json['individualsByGuid']['I000001_na19675'].keys()), INDIVIDUAL_FIELDS)
        self.assertListEqual(
            response_json['individualsByGuid']['I000001_na19675']['features'],
            [{'id': 'HP:0002017', 'category': 'HP:0025031', 'label': 'Nausea and vomiting'}]
        )
        self.assertListEqual(
            response_json['individualsByGuid']['I000001_na19675']['absentFeatures'],
            [{'id': 'HP:0012469', 'category': 'HP:0025031', 'label': 'Infantile spasms'}]
        )
        self.assertEqual(response_json['individualsByGuid']['I000001_na19675']['sex'], 'M')
        self.assertEqual(response_json['individualsByGuid']['I000001_na19675']['birthYear'], 2000)
        self.assertTrue(response_json['individualsByGuid']['I000001_na19675']['affectedRelatives'])
        self.assertEqual(response_json['individualsByGuid']['I000001_na19675']['onsetAge'], 'J')
        self.assertListEqual(response_json['individualsByGuid']['I000001_na19675']['expectedInheritance'], ['D', 'S'])
        self.assertListEqual(
            response_json['individualsByGuid']['I000001_na19675']['maternalEthnicity'], ['Finnish', 'Irish'])
        self.assertListEqual(
            response_json['individualsByGuid']['I000001_na19675']['candidateGenes'],
            [{'gene': 'IKBKAP', 'comments': 'multiple panels, no confirm'}, {'gene': 'EHBP1L1'}])

        if expected_families:
            self.assertListEqual(list(response_json['familiesByGuid'].keys()), ['F000001_1'])
            self.assertDictEqual(
                response_json['familiesByGuid']['F000001_1']['assignedAnalyst'],
                {'email': 'test_user_collaborator@test.com', 'fullName': 'Test Collaborator User'}
            )

    def test_individuals_metadata_table_handler(self):
        url = reverse(receive_individuals_metadata_handler, args=['R0001_1kg'])
        self.check_collaborator_login(url)

        # Send invalid requests
        header = 'family_id,indiv_id,hpo_term_yes,hpo_term_no'
        f = SimpleUploadedFile('updates.csv', header.encode('utf-8'))
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Invalid header, missing individual id column'], 'warnings': []})

        header = 'family_id,individual_id,hpo_term_present,hpo_term_absent,sex,birth year,other affected relatives,onset age,expected inheritance,maternal ancestry,candidate genes,assigned analyst'
        rows = [
            '1,NA19678,,,,,no,infant,recessive,,,not_an_email',
            '1,NA19679,HP:0100258 (Preaxial polydactyly),,,,,,,,,test_user_no_access@test.com',
            '1,HG00731,HP:0002017,HP:0012469 (Infantile spasms);HP:0011675 (Arrhythmia),,,,,,,,,',
        ]
        f = SimpleUploadedFile('updates.csv', "{}\n{}".format(header, '\n'.join(rows)).encode('utf-8'))
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': [
                'Unable to find individuals to update for any of the 3 parsed individuals. No matching ids found for 1 individuals. No changes detected for 2 individuals.'
            ],
            'warnings': [
                "The following HPO terms were not found in seqr's HPO data and will not be added: HP:0100258 (NA19679)",
                'The following invalid values for "affected_relatives" will not be added: no (NA19678)',
                'The following invalid values for "onset_age" will not be added: infant (NA19678)',
                'The following invalid values for "expected_inheritance" will not be added: recessive (NA19678)',
                'The following invalid values for "assigned_analyst" will not be added: not_an_email (NA19678); test_user_no_access@test.com (NA19679)',
                'Unable to find matching ids for 1 individuals. The following entries will not be updated: HG00731',
                'No changes detected for 2 individuals. The following entries will not be updated: NA19678, NA19679',
            ]})

        # send valid request
        rows[0] = '1,NA19678,,,,,,,,,,'
        rows.append('1,NA19675_1,HP:0002017,"HP:0012469 (Infantile spasms);HP:0004322 (Short stature, severe)",F,2000,True,Juvenile onset,"Autosomal dominant inheritance, Sporadic","Finnish, Irish","IKBKAP -- (multiple panels, no confirm), EHBP1L1",test_user_collaborator@test.com')
        f = SimpleUploadedFile('updates.csv', "{}\n{}".format(header, '\n'.join(rows)).encode('utf-8'))
        response = self.client.post(url, data={'f': f})
        self._is_expected_individuals_metadata_upload(response, expected_families=True)

    def test_individuals_metadata_json_table_handler(self):
        url = reverse(receive_individuals_metadata_handler, args=['R0001_1kg'])
        self.check_collaborator_login(url)

        f = SimpleUploadedFile('updates.json', json.dumps([
            {'external_id': 'NA19675_1', 'sex': 'F', 'date_of_birth': '2000-01-01', 'features': [
                {'id': 'HP:0002017', 'observed': 'yes'},
                {'id': 'HP:0012469', 'observed': 'no'},
                {'id': 'HP:0004322', 'observed': 'no'},
            ], 'family_history': {'affectedRelatives': True}, 'global_age_of_onset': [{'label': 'Juvenile onset'}],
             'global_mode_of_inheritance': [{'label': 'Autosomal dominant inheritance'}, {'label': 'Sporadic'}],
             'ethnicity': {'maternal_ethnicity': ['Finnish', 'Irish']}, 'genes': [
                 {'gene': 'IKBKAP', 'comments': 'multiple panels, no confirm'}, {'gene': 'EHBP1L1'},
             ]},
            {'external_id': 'NA19678', 'features': [], 'notes': {'family_history': 'history note'}},
            {'external_id': 'NA19679', 'features': [{'id': 'HP:0100258', 'observed': 'yes'}]},
            {'family_id': '1', 'external_id': 'HG00731', 'features': [
                {'id': 'HP:0002017', 'observed': 'yes'}, {'id': 'HP:0011675', 'observed': 'no'}]},
        ]).encode('utf-8'))
        response = self.client.post(url, data={'f': f})
        self._is_expected_individuals_metadata_upload(response)

    def test_individuals_metadata_hpo_term_number_table_handler(self):
        url = reverse(receive_individuals_metadata_handler, args=['R0001_1kg'])
        self.check_collaborator_login(url)

        header = 'family_id,individual_id,affected,hpo_number,hpo_number,sex,birth,other affected relatives,onset,expected inheritance,maternal ancestry,candidate genes'
        rows = [
            '1,NA19675_1,yes,HP:0002017,,F,2000,true,Juvenile onset,"Autosomal dominant inheritance, Sporadic","Finnish, Irish","IKBKAP -- (multiple panels, no confirm), EHBP1L1"',
            '1,NA19675_1,no,HP:0012469,,,,,,,,',
            '1,NA19675_1,no,,HP:0004322,,,,,,,',
            '1,NA19678,,,,,,,,,,',
            '1,NA19679,yes,HP:0100258,,,,,,,,',
            '1,HG00731,yes,HP:0002017,,,,,,,,',
            '1,HG00731,no,HP:0012469,HP:0011675,,,,,,,',
        ]
        f = SimpleUploadedFile('updates.csv', "{}\n{}".format(header, '\n'.join(rows)).encode('utf-8'))
        response = self.client.post(url, data={'f': f})
        self._is_expected_individuals_metadata_upload(response)

    def test_get_hpo_terms(self):
        url = reverse(get_hpo_terms, args=['HP:0011458'])
        self.check_require_login(url)

        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'HP:0011458': {
                'HP:0002017': {'id': 'HP:0002017', 'category': 'HP:0025031', 'label': 'Nausea and vomiting'},
                'HP:0001252': {'id': 'HP:0001252', 'category': 'HP:0025031', 'label': 'Muscular hypotonia'},
            }
        })

        url = reverse(get_hpo_terms, args=['HP:0002017'])
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'HP:0002017': {}
        })

    def test_get_individual_rna_seq_data(self):
        url = reverse(get_individual_rna_seq_data, args=[INDIVIDUAL_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'rnaSeqData', 'genesById'})
        self.assertDictEqual(response_json['rnaSeqData'], {
            INDIVIDUAL_GUID: {'outliers': {
                'ENSG00000135953': {
                    'geneId': 'ENSG00000135953', 'zScore': 7.31, 'pValue': 0.00000000000948, 'pAdjust': 0.00000000781,
                    'isSignificant': True,
                },
                'ENSG00000240361': {
                    'geneId': 'ENSG00000240361', 'zScore': -4.08, 'pValue': 5.88, 'pAdjust': 0.09, 'isSignificant': False,
                },
                'ENSG00000268903': {
                    'geneId': 'ENSG00000268903', 'zScore': 7.08, 'pValue':0.000000000588, 'pAdjust': 0.00000000139,
                    'isSignificant': True,
                },
            }}
        })
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000135953', 'ENSG00000268903'})

