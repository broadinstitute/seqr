# -*- coding: utf-8 -*-
import json

from django.urls.base import reverse

from seqr.views.apis.case_review_api import save_internal_case_review_notes, save_internal_case_review_summary
from seqr.views.utils.test_utils import AuthenticationTestCase

FAMILY_GUID = 'F000001_1'
NO_CASE_REVIEW_FAMILY_GUID = 'F000011_11'

PROJECT_GUID = 'R0001_1kg'


class CaseReviewAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    def test_save_internal_case_review_notes(self):
        url = reverse(save_internal_case_review_notes, args=[FAMILY_GUID])
        self.check_manager_login(url)

        # send request with a "value" attribute
        req_values = {
            'value': 'some case review notes'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['familyGuid'], FAMILY_GUID)
        self.assertEqual(response_json[FAMILY_GUID]['caseReviewNotes'], req_values['value'])

        # send request with a invalid "value" attribute
        invalid_req_values = {
            'valueX': 'some case review notes'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(invalid_req_values))
        self.assertEqual(response.status_code, 500)

        # send request for invalid project
        url = reverse(save_internal_case_review_notes, args=[NO_CASE_REVIEW_FAMILY_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps(req_values))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'User cannot edit case_review_notes for this project')

    def test_save_internal_case_review_summary(self):
        url = reverse(save_internal_case_review_summary, args=[FAMILY_GUID])
        self.check_manager_login(url)

        # send request with a "value" attribute
        req_values = {
            'value': 'some case review notes'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['familyGuid'], FAMILY_GUID)
        self.assertEqual(response_json[FAMILY_GUID]['caseReviewSummary'], req_values['value'])
        # send request with a "value" attribute
        invalid_req_values = {
            'valueX': 'some case review notes'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(invalid_req_values))
        self.assertEqual(response.status_code, 500)

        # send request for invalid project
        url = reverse(save_internal_case_review_summary, args=[NO_CASE_REVIEW_FAMILY_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps(req_values))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'User cannot edit case_review_summary for this project')
