# -*- coding: utf-8 -*-
import json
import mock

from datetime import datetime
from django.urls.base import reverse

from seqr.views.apis.case_review_api import save_internal_case_review_notes, save_internal_case_review_summary, \
    update_case_review_status, update_case_review_discussion
from seqr.views.utils.test_utils import AuthenticationTestCase

PROJECT_GUID = 'R0001_1kg'

FAMILY_GUID = 'F000001_1'
NO_CASE_REVIEW_FAMILY_GUID = 'F000011_11'

INDIVIDUAL_GUID = 'I000007_na20870'
NO_CASE_REVIEW_INDIVIDUAL_GUID = 'I000015_na20885'

class CaseReviewAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    def _test_save_internal_case_review_field(self, url_func, field):
        url = reverse(url_func, args=[FAMILY_GUID])
        self.check_manager_login(url)

        req_values = {
            field: 'some case review notes'
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['familyGuid'], FAMILY_GUID)
        self.assertEqual(response_json[FAMILY_GUID][field], 'some case review notes')

        # send request for invalid project
        url = reverse(url_func, args=[NO_CASE_REVIEW_FAMILY_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps(req_values))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

    def test_save_internal_case_review_notes(self):
        self._test_save_internal_case_review_field(save_internal_case_review_notes, 'caseReviewNotes')

    def test_save_internal_case_review_summary(self):
        self._test_save_internal_case_review_field(save_internal_case_review_summary, 'caseReviewSummary')

    @mock.patch('seqr.views.utils.json_to_orm_utils.timezone.now', lambda: datetime.strptime('2020-01-01', '%Y-%m-%d'))
    def test_update_case_review_status(self):
        url = reverse(update_case_review_status, args=[INDIVIDUAL_GUID])
        self.check_manager_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'caseReviewStatus': 'A'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), [INDIVIDUAL_GUID])
        self.assertEqual(response_json[INDIVIDUAL_GUID]['caseReviewStatus'], 'A')
        self.assertEqual(response_json[INDIVIDUAL_GUID]['caseReviewStatusLastModifiedDate'],
                         '2020-01-01T00:00:00')
        self.assertEqual(response_json[INDIVIDUAL_GUID]['caseReviewStatusLastModifiedBy'], 'Test Manager User')

        # send request for invalid project
        url = reverse(update_case_review_status, args=[NO_CASE_REVIEW_INDIVIDUAL_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps({'caseReviewStatus': 'A'}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

    def test_update_case_review_discussion(self):
        url = reverse(update_case_review_discussion, args=[INDIVIDUAL_GUID])
        self.check_manager_login(url)

        response = self.client.post(
            url, content_type='application/json', data=json.dumps({'caseReviewDiscussion': 'A Note'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), [INDIVIDUAL_GUID])
        self.assertEqual(response_json[INDIVIDUAL_GUID]['caseReviewDiscussion'], 'A Note')

        # send request for invalid project
        url = reverse(update_case_review_discussion, args=[NO_CASE_REVIEW_INDIVIDUAL_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps({'caseReviewDiscussion': 'A Note'}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')
