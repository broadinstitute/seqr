# -*- coding: utf-8 -*-
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.case_review_api import save_internal_case_review_notes, save_internal_case_review_summary
from seqr.views.utils.test_utils import _check_login

FAMILY_GUID = 'F000001_1'

PROJECT_GUID = 'R0001_1kg'


class CaseReviewAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_save_internal_case_review_notes(self):
        url = reverse(save_internal_case_review_notes, args=[FAMILY_GUID])
        _check_login(self, url)

        # send request with a "value" attribute
        req_values = {
            'value': 'some case review notes'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['familyGuid'], FAMILY_GUID)
        self.assertEqual(response_json[FAMILY_GUID]['internalCaseReviewNotes'], req_values['value'])
        # send request with a "value" attribute
        req_values = {
            'valueX': 'some case review notes'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 500)

    def test_save_internal_case_review_summary(self):
        url = reverse(save_internal_case_review_summary, args=[FAMILY_GUID])
        _check_login(self, url)

        # send request with a "value" attribute
        req_values = {
            'value': 'some case review notes'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['familyGuid'], FAMILY_GUID)
        self.assertEqual(response_json[FAMILY_GUID]['internalCaseReviewSummary'], req_values['value'])
        # send request with a "value" attribute
        req_values = {
            'valueX': 'some case review notes'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 500)
