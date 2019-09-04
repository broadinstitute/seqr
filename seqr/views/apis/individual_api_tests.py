# -*- coding: utf-8 -*-

import json
import mock

from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.individual_api import edit_individuals_handler
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

    @mock.patch('seqr.utils.model_sync_utils.find_matching_xbrowse_model')
    def test_edit_individuals(self, mock_find_xbrowse_model):
        mock_find_xbrowse_model.return_value.has_elasticsearch_index.return_value = False

        edit_individuals_url = reverse(edit_individuals_handler, args=[PROJECT_GUID])
        _check_login(self, edit_individuals_url)

        # send invalid requests
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ["NA20870 is the mother of NA19678_1 but doesn't have a separate record in the table"])

        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA, INDIVIDUAL_FAMILY_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Editing individual_id is disabled for projects which still use the mongo datastore'])

        # send valid request
        mock_find_xbrowse_model.return_value.has_elasticsearch_index.return_value = True
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA, INDIVIDUAL_FAMILY_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual({'F000001_1', 'F000003_3'}, set(response_json['familiesByGuid']))
        self.assertSetEqual({ID_UPDATE_GUID, FAMILY_UPDATE_GUID, CHILD_UPDATE_GUID, "I000003_na19679"},
                            set(response_json['familiesByGuid']['F000001_1']['individualGuids']))
        self.assertListEqual(response_json['familiesByGuid']['F000003_3']['individualGuids'], [])

        self.assertSetEqual({ID_UPDATE_GUID, FAMILY_UPDATE_GUID, CHILD_UPDATE_GUID}, set(response_json['individualsByGuid']))
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['individualId'], UPDATED_ID)
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['maternalId'], UPDATED_MATERNAL_ID)
        self.assertEqual(response_json['individualsByGuid'][CHILD_UPDATE_GUID]['paternalId'], UPDATED_ID)
