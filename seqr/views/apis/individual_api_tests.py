# -*- coding: utf-8 -*-

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.individual_api import edit_individuals_handler, update_individual_handler, \
    delete_individuals_handler, receive_individuals_table_handler, save_individuals_table_handler
from seqr.views.utils.test_utils import _check_login

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

FAMILY_UPDATE_GUID = "I000007_na20870"
INDIVIDUAL_FAMILY_UPDATE_DATA = {
    "individualGuid": FAMILY_UPDATE_GUID,
    "familyId": "1",
    "individualId": UPDATED_MATERNAL_ID,
}

CHILD_UPDATE_GUID = "I000001_na19675"


class IndividualAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_update_individual_handler(self):
        edit_individuals_url = reverse(update_individual_handler, args=[ID_UPDATE_GUID])
        _check_login(self, edit_individuals_url)

        response = self.client.post(edit_individuals_url, content_type='application/json',
                                    data=json.dumps(INDIVIDUAL_FAMILY_UPDATE_DATA))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), [ID_UPDATE_GUID])

    def test_edit_individuals(self):
        edit_individuals_url = reverse(edit_individuals_handler, args=[PROJECT_GUID])
        _check_login(self, edit_individuals_url)

        # send invalid requests
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
        _check_login(self, individuals_url)

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
        _check_login(self, individuals_url)

        data = 'Family ID	Individual ID	Paternal ID	Maternal ID	Sex	Affected Status	Notes\n\
"1"	"NA19675"	"NA19678"	"NA19679"	"Female"	"Affected"	"A affected individual, test1-zsf"\n\
"1"	"NA19678"	""	""	"Male"	"Unaffected"	"a individual note"\n\
"2"	"HG00733"	""	""	"Female"	"Unaffected"	""'

        f = SimpleUploadedFile("1000_genomes demo_individuals.tsv", data)

        response = self.client.post(individuals_url, {'f': f})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['info', 'errors', 'warnings', 'uploadedFileId'])

        url = reverse(save_individuals_table_handler, args=[PROJECT_GUID, response_json['uploadedFileId']])

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['individualsByGuid', 'familiesByGuid'])