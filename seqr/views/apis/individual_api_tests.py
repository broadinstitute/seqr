# -*- coding: utf-8 -*-

import json
import mock

from datetime import datetime
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls.base import reverse

from seqr.models import Individual
from seqr.views.apis.individual_api import edit_individuals_handler, update_individual_handler, \
    delete_individuals_handler, receive_individuals_table_handler, save_individuals_table_handler, \
    receive_hpo_table_handler, save_hpo_table_handler, update_individual_hpo_terms, get_hpo_terms
from seqr.views.utils.test_utils import AuthenticationTestCase, INDIVIDUAL_FIELDS

PROJECT_GUID = 'R0001_1kg'

ID_UPDATE_GUID = "I000002_na19678"
UPDATED_ID = "NA19678_1"
UPDATED_MATERNAL_ID = "NA20870"

INDIVIDUAL_IDS_UPDATE_DATA = {
    "individualGuid": ID_UPDATE_GUID,
    "familyId": "1",
    "individualId": UPDATED_ID,
    "maternalId": UPDATED_MATERNAL_ID,
    "paternalId": "",
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

FAMILY_UPDATE_GUID = "I000007_na20870"
INDIVIDUAL_FAMILY_UPDATE_DATA = {
    "individualGuid": FAMILY_UPDATE_GUID,
    "familyId": "1",
    "individualId": UPDATED_MATERNAL_ID,
}

CHILD_UPDATE_GUID = "I000001_na19675"


class IndividualAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    @mock.patch('seqr.views.utils.json_to_orm_utils.timezone.now', lambda: datetime.strptime('2020-01-01', '%Y-%m-%d'))
    def test_update_individual_handler(self):
        edit_individuals_url = reverse(update_individual_handler, args=[INDIVIDUAL_UPDATE_GUID])
        self.check_manager_login(edit_individuals_url)

        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps(INDIVIDUAL_UPDATE_DATA))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), [INDIVIDUAL_UPDATE_GUID])
        individual = Individual.objects.get(guid=INDIVIDUAL_UPDATE_GUID)
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['displayName'], 'NA20870')
        self.assertEqual(individual.display_name, '')
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['notes'], 'A note')
        self.assertFalse('features' in response_json[INDIVIDUAL_UPDATE_GUID])
        self.assertIsNone(individual.features)

        # test edit case review status
        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps({'caseReviewStatus': 'A'}))
        self.assertEqual(response.status_code, 403)
        self.login_staff_user()
        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps({'caseReviewStatus': 'A'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), [INDIVIDUAL_UPDATE_GUID])
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['caseReviewStatus'], 'A')
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['caseReviewStatusLastModifiedDate'], '2020-01-01T00:00:00')
        self.assertEqual(response_json[INDIVIDUAL_UPDATE_GUID]['caseReviewStatusLastModifiedBy'], 'test_user@test.com')

    def test_update_individual_hpo_terms(self):
        edit_individuals_url = reverse(update_individual_hpo_terms, args=[INDIVIDUAL_UPDATE_GUID])
        self.check_manager_login(edit_individuals_url)

        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps(INDIVIDUAL_UPDATE_DATA))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), [INDIVIDUAL_UPDATE_GUID])
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

    def test_edit_individuals(self):
        edit_individuals_url = reverse(edit_individuals_handler, args=[PROJECT_GUID])
        self.check_staff_login(edit_individuals_url)

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

    def test_delete_individuals(self):
        individuals_url = reverse(delete_individuals_handler, args=[PROJECT_GUID])
        self.check_staff_login(individuals_url)

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
        self.assertListEqual(response_json.keys(), ['individualsByGuid', 'familiesByGuid'])

    def test_individuals_table_handler(self):
        individuals_url = reverse(receive_individuals_table_handler, args=[PROJECT_GUID])
        self.check_staff_login(individuals_url)

        # send invalid requests
        response = self.client.get(individuals_url)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Received 0 files instead of 1'], 'warnings': []})

        response = self.client.post(individuals_url, {'f': SimpleUploadedFile('test.tsv', 'family   indiv\n1    ')})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': [
            "Error while converting test.tsv rows to json: Individual Id not specified in row #1:\n{'familyId': u'1'}"
        ], 'warnings': []})

        response = self.client.post(individuals_url, {'f': SimpleUploadedFile(
            'test.tsv', 'Family ID	Individual ID	Previous Individual ID\n"1"	"NA19675_1"	"NA19675"')})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': ['Could not find individuals with the following previous IDs: NA19675'], 'warnings': []
        })

        # send valid requests
        data = 'Family ID	Individual ID	Previous Individual ID	Paternal ID	Maternal ID	Sex	Affected Status	Notes	familyNotes\n\
"1"	"NA19675"	"NA19675_1"	"NA19678"	"NA19679"	"Female"	"Affected"	"A affected individual, test1-zsf"	""\n\
"1"	"NA19678"	""	""	""	"Male"	"Unaffected"	"a individual note"	""\n\
"21"	"HG00735"	""	""	""	"Female"	"Unaffected"	""	"a new family"'

        f = SimpleUploadedFile("1000_genomes demo_individuals.tsv", data)

        response = self.client.post(individuals_url, {'f': f})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['info', 'errors', 'warnings', 'uploadedFileId'])

        url = reverse(save_individuals_table_handler, args=[PROJECT_GUID, response_json['uploadedFileId']])

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'individualsByGuid', 'familiesByGuid'})

    def _is_expected_hpo_upload(self, response):
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
        url = reverse(save_hpo_table_handler, args=[PROJECT_GUID, response_json['uploadedFileId']])

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['individualsByGuid'])
        self.assertListEqual(response_json['individualsByGuid'].keys(), ['I000001_na19675'])
        self.assertSetEqual(set(response_json['individualsByGuid']['I000001_na19675'].keys()), INDIVIDUAL_FIELDS)
        self.assertListEqual(
            response_json['individualsByGuid']['I000001_na19675']['features'],
            [{'id': 'HP:0002017', 'category': 'HP:0025031', 'label': 'Nausea and vomiting'}]
        )
        self.assertListEqual(
            response_json['individualsByGuid']['I000001_na19675']['absentFeatures'],
            [{'id': 'HP:0012469', 'category': 'HP:0025031', 'label': 'Infantile spasms'}]
        )

    def test_hpo_table_handler(self):
        url = reverse(receive_hpo_table_handler, args=['R0001_1kg'])
        self.check_collaborator_login(url)

        # Send invalid requests
        header = 'family_id,indiv_id,hpo_term_yes,hpo_term_no'
        f = SimpleUploadedFile('updates.csv', header)
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Invalid header, missing individual id column'], 'warnings': []})

        header = 'family_id,individual_id,hpo_term_yes,hpo_term_no'
        f = SimpleUploadedFile('updates.csv', header)
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Invalid header, missing hpo terms columns'], 'warnings': []})

        header = 'family_id,individual_id,hpo_term_present,hpo_term_absent'
        rows = [
            '1,NA19678,,',
            '1,NA19679,HP:0100258 (Preaxial polydactyly),',
            '1,HG00731,HP:0002017,HP:0012469 (Infantile spasms);HP:0011675 (Arrhythmia)',
        ]
        f = SimpleUploadedFile('updates.csv', "{}\n{}".format(header, '\n'.join(rows)))
        response = self.client.post(url, data={'f': f})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': [
                'Unable to find individuals to update for any of the 3 parsed individuals. No matching ids found for 1 individuals. No changes detected for 2 individuals.'
            ],
            'warnings': [
                "The following HPO terms were not found in seqr's HPO data and will not be added: HP:0100258 (NA19679)",
                'Unable to find matching ids for 1 individuals. The following entries will not be updated: HG00731',
                'No changes detected for 2 individuals. The following entries will not be updated: NA19678, NA19679',
            ]})

        # send valid request
        rows.append('1,NA19675_1,HP:0002017,HP:0012469 (Infantile spasms);HP:0004322 (Short stature)')
        f = SimpleUploadedFile('updates.csv', "{}\n{}".format(header, '\n'.join(rows)))
        response = self.client.post(url, data={'f': f})
        self._is_expected_hpo_upload(response)

    def test_hpo_json_table_handler(self):
        url = reverse(receive_hpo_table_handler, args=['R0001_1kg'])
        self.check_collaborator_login(url)

        f = SimpleUploadedFile('updates.json', json.dumps([
            {'family_id': '1', 'external_id': 'NA19675_1', 'features': [
                {'id': 'HP:0002017', 'observed': 'yes'},
                {'id': 'HP:0012469', 'observed': 'no'},
                {'id': 'HP:0004322', 'observed': 'no'}]},
            {'family_id': '1', 'external_id': 'NA19678', 'features': []},
            {'family_id': '1', 'external_id': 'NA19679', 'features': [{'id': 'HP:0100258', 'observed': 'yes'}]},
            {'family_id': '1', 'external_id': 'HG00731', 'features': [
                {'id': 'HP:0002017', 'observed': 'yes'}, {'id': 'HP:0011675', 'observed': 'no'}]},
        ]))
        response = self.client.post(url, data={'f': f})
        self._is_expected_hpo_upload(response)

    def test_hpo_term_number_table_handler(self):
        url = reverse(receive_hpo_table_handler, args=['R0001_1kg'])
        self.check_collaborator_login(url)

        header = 'family_id,individual_id,affected,hpo_number,hpo_number'
        rows = [
            '1,NA19675_1,yes,HP:0002017,',
            '1,NA19675_1,no,HP:0012469,',
            '1,NA19675_1,no,,HP:0004322',
            '1,NA19678,,,',
            '1,NA19679,yes,HP:0100258,',
            '1,HG00731,yes,HP:0002017,',
            '1,HG00731,no,HP:0012469,HP:0011675',
        ]
        f = SimpleUploadedFile('updates.csv', "{}\n{}".format(header, '\n'.join(rows)))
        response = self.client.post(url, data={'f': f})
        self._is_expected_hpo_upload(response)

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

