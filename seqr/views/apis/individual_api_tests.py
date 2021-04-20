# -*- coding: utf-8 -*-
import json
import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls.base import reverse

from seqr.models import Individual
from seqr.views.apis.individual_api import edit_individuals_handler, update_individual_handler, \
    delete_individuals_handler, receive_individuals_table_handler, save_individuals_table_handler, \
    receive_individuals_metadata_handler, save_individuals_metadata_table_handler, update_individual_hpo_terms, get_hpo_terms
from seqr.views.utils.test_utils import AuthenticationTestCase, INDIVIDUAL_FIELDS

PROJECT_GUID = 'R0001_1kg'
PM_REQUIRED_PROJECT_GUID = 'R0003_test'

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

PM_REQUIRED_INDIVIDUAL_UPDATE_DATA = {'individualGuid': 'I000017_na20889', 'individualId': 'NA20889', 'familyId': '12'}

FAMILY_UPDATE_GUID = "I000007_na20870"
INDIVIDUAL_FAMILY_UPDATE_DATA = {
    "individualGuid": FAMILY_UPDATE_GUID,
    "familyId": "1",
    "individualId": UPDATED_MATERNAL_ID,
}

CHILD_UPDATE_GUID = "I000001_na19675"


class IndividualAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    def test_update_individual_handler(self):
        edit_individuals_url = reverse(update_individual_handler, args=[INDIVIDUAL_UPDATE_GUID])
        self.check_manager_login(edit_individuals_url)

        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps(INDIVIDUAL_UPDATE_DATA))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), [INDIVIDUAL_UPDATE_GUID])
        individual = Individual.objects.get(guid=INDIVIDUAL_UPDATE_GUID)
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['displayName'], 'NA20870')
        self.assertEqual(individual.display_name, '')
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['notes'], 'A note')
        self.assertFalse('features' in response_json[INDIVIDUAL_UPDATE_GUID])
        self.assertIsNone(individual.features)

    def test_update_individual_hpo_terms(self):
        edit_individuals_url = reverse(update_individual_hpo_terms, args=[INDIVIDUAL_UPDATE_GUID])
        self.check_manager_login(edit_individuals_url)

        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps(INDIVIDUAL_UPDATE_DATA))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), [INDIVIDUAL_UPDATE_GUID])
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['displayName'], 'NA20870')
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
    @mock.patch('seqr.views.utils.pedigree_image_utils._update_pedigree_image')
    def test_edit_individuals(self, mock_update_pedigree, mock_pm_group):
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
        self.assertListEqual(response.json()['errors'],
                             ["NA20870 is the mother of NA19678_1 but doesn't have a separate record in the table"])

        # send valid request
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA, INDIVIDUAL_FAMILY_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual({'F000001_1', 'F000003_3'}, set(response_json['familiesByGuid']))
        self.assertSetEqual({ID_UPDATE_GUID, FAMILY_UPDATE_GUID, CHILD_UPDATE_GUID, "I000003_na19679"},
                            set(response_json['familiesByGuid']['F000001_1']['individualGuids']))
        self.assertListEqual(response_json['familiesByGuid']['F000003_3']['individualGuids'], [])

        self.assertSetEqual({ID_UPDATE_GUID, FAMILY_UPDATE_GUID, CHILD_UPDATE_GUID},
                            set(response_json['individualsByGuid']))
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['individualId'], UPDATED_ID)
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['maternalId'], UPDATED_MATERNAL_ID)
        self.assertEqual(response_json['individualsByGuid'][CHILD_UPDATE_GUID]['paternalId'], UPDATED_ID)
        self.assertSetEqual(
            {'F000001_1', 'F000003_3'},
            {call_arg.args[0].guid for call_arg in mock_update_pedigree.call_args_list}
        )

        # test only updating parental IDs
        mock_update_pedigree.reset_mock()
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

        self.assertSetEqual({'F000001_1'}, set(response_json['familiesByGuid']))
        self.assertSetEqual({ID_UPDATE_GUID}, set(response_json['individualsByGuid']))
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['individualId'], UPDATED_ID)
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['maternalId'], 'NA19679')
        self.assertSetEqual({'F000001_1'}, {call_arg.args[0].guid for call_arg in mock_update_pedigree.call_args_list})

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

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    @mock.patch('seqr.views.utils.pedigree_image_utils._update_pedigree_image')
    def test_delete_individuals(self, mock_update_pedigree, mock_pm_group):
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

        mock_update_pedigree.assert_called_once()
        self.assertEqual(mock_update_pedigree.call_args.args[0].guid, 'F000001_1')

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
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    @mock.patch('seqr.views.utils.pedigree_image_utils._update_pedigree_image')
    def test_individuals_table_handler(self, mock_update_pedigree):
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
        self.assertEqual(errors[0].split('\n')[0],"Error while converting test.tsv rows to json: Individual Id not specified in row #1:")

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
            'errors': ["NA19678_dad is the father of NA19675_1 but doesn't have a separate record in the table"], 'warnings': []
        })

        # send valid requests
        data = 'Family ID	Individual ID	Previous Individual ID	Paternal ID	Maternal ID	Sex	Affected Status	Notes	familyNotes\n\
"1"	"NA19675"	"NA19675_1"	"NA19678"	"NA19679"	"Female"	"Affected"	"A affected individual, test1-zsf"	""\n\
"1"	"NA19678"	""	""	""	"Male"	"Unaffected"	"a individual note"	""\n\
"21"	"HG00735"	""	""	""	"Female"	"Unaffected"	""	"a new family"'

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
        mock_update_pedigree.assert_not_called()

        url = reverse(save_individuals_table_handler, args=[PROJECT_GUID, response_json['uploadedFileId']])

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'individualsByGuid', 'familiesByGuid'})

        self.assertEqual(len(response_json['familiesByGuid']), 2)
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        new_family_guid = next(guid for guid in response_json['familiesByGuid'].keys() if guid != 'F000001_1')
        self.assertEqual(response_json['familiesByGuid'][new_family_guid]['familyId'], '21')
        self.assertEqual(response_json['familiesByGuid'][new_family_guid]['analysisNotes'], 'a new family')

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

        self.assertSetEqual(
            {'F000001_1', new_family_guid},
            {call_arg.args[0].guid for call_arg in mock_update_pedigree.call_args_list}
        )

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

    def _is_expected_individuals_metadata_upload(self, response):
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json, {
            'uploadedFileId': mock.ANY,
            'errors': [],
            'warnings': [
                "The following HPO terms were not found in seqr's HPO data and will not be added: HP:0004322 (NA19675_1); HP:0100258 (NA19679)",
                'Unable to find matching ids for 1 individuals. The following entries will not be updated: HG00731',
                'No changes detected for 2 individuals. The following entries will not be updated: NA19678, NA19679',
            ],
            'info': ['1 individuals will be updated'],
        })

        # Save uploaded file
        url = reverse(save_individuals_metadata_table_handler, args=[PROJECT_GUID, response_json['uploadedFileId']])

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['individualsByGuid'])
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

    def test_individuals_metadata_table_handler(self):
        url = reverse(receive_individuals_metadata_handler, args=['R0001_1kg'])
        self.check_collaborator_login(url)

        # Send invalid requests
        header = 'family_id,indiv_id,hpo_term_yes,hpo_term_no'
        f = SimpleUploadedFile('updates.csv', header.encode('utf-8'))
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Invalid header, missing individual id column'], 'warnings': []})

        header = 'family_id,individual_id,hpo_term_present,hpo_term_absent,sex,birth year,other affected relatives,onset age,expected inheritance,maternal ancestry,candidate genes'
        rows = [
            '1,NA19678,,,,,no,infant,recessive,,',
            '1,NA19679,HP:0100258 (Preaxial polydactyly),,,,,,,,',
            '1,HG00731,HP:0002017,HP:0012469 (Infantile spasms);HP:0011675 (Arrhythmia),,,,,,,',
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
                'Unable to find matching ids for 1 individuals. The following entries will not be updated: HG00731',
                'No changes detected for 2 individuals. The following entries will not be updated: NA19678, NA19679',
            ]})

        # send valid request
        rows[0] = '1,NA19678,,,,,,,,,'
        rows.append('1,NA19675_1,HP:0002017,"HP:0012469 (Infantile spasms);HP:0004322 (Short stature, severe)",F,2000,True,Juvenile onset,"Autosomal dominant inheritance, Sporadic","Finnish, Irish","IKBKAP -- (multiple panels, no confirm), EHBP1L1"')
        f = SimpleUploadedFile('updates.csv', "{}\n{}".format(header, '\n'.join(rows)).encode('utf-8'))
        response = self.client.post(url, data={'f': f})
        self._is_expected_individuals_metadata_upload(response)

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

