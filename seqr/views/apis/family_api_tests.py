# -*- coding: utf-8 -*-
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls.base import reverse

from seqr.views.apis.family_api import update_family_pedigree_image, update_family_assigned_analyst, \
    update_family_fields_handler, update_family_analysed_by, edit_families_handler, delete_families_handler, receive_families_table_handler
from seqr.views.utils.test_utils import _check_login

FAMILY_GUID = 'F000001_1'
FAMILY_GUID2 = 'F000002_2'

PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'

FAMILY_ID_FIELD = 'familyId'
PREVIOUS_FAMILY_ID_FIELD = 'previousFamilyId'


class ProjectAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    #  TODO test other family api methods

    def test_edit_families_handler(self):
        url = reverse(edit_families_handler, args=[PROJECT_GUID])
        _check_login(self, url)

        # send request with a "families" attribute
        req_values = {
            'families': [
                {'familyGuid': FAMILY_GUID, 'description': 'Test description 1'},
                {PREVIOUS_FAMILY_ID_FIELD: '2', 'description': 'Test description 2'},
                {FAMILY_ID_FIELD: '13', 'description': 'Test description 13'}
            ]
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['familiesByGuid'])
        self.assertEqual(response_json['familiesByGuid'][FAMILY_GUID]['description'], 'Test description 1')
        self.assertEqual(response_json['familiesByGuid'][FAMILY_GUID2]['description'], 'Test description 2')
        self.assertEqual(response_json['familiesByGuid']['F000013_13']['description'], 'Test description 13')

    def test_delete_families_handler(self):
        url = reverse(delete_families_handler, args=[PROJECT_GUID])
        _check_login(self, url)

        # send request with a "families" attribute to provide a list of families
        req_values = {
            'families': [
                {'familyGuid': FAMILY_GUID},
                {'familyGuid': FAMILY_GUID2}
            ]
        }
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps(req_values))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), ['individualsByGuid', 'familiesByGuid'])
        self.assertIsNone(response_json['familiesByGuid'][FAMILY_GUID])
        self.assertIsNone(response_json['familiesByGuid'][FAMILY_GUID2])

        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'families': None}))
        self.assertEqual(response.status_code, 400)

    def test_update_family_analysed_by(self):
        url = reverse(update_family_analysed_by, args=[FAMILY_GUID])
        _check_login(self, url)

        # send request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['analysedBy'][0]['createdBy']['fullName'], 'Test User')

    def test_update_family_pedigree_image(self):
        url = reverse(update_family_pedigree_image, args=[FAMILY_GUID])
        _check_login(self, url)

        f = SimpleUploadedFile("new_ped_image_123.png", b"file_content")

        # send invalid request
        response = self.client.post(url, {'f1': f, 'f2': f})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Received 2 files')

        # send valid add/update request
        response = self.client.post(url, {'f': f})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), [FAMILY_GUID])
        self.assertRegex(response_json[FAMILY_GUID]['pedigreeImage'], '/media/pedigree_images/new_ped_image_.+\.png')

        # send valid delete request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), [FAMILY_GUID])
        self.assertIsNone(response_json[FAMILY_GUID]['pedigreeImage'])

    def test_update_family_assigned_analyst(self):
        url = reverse(update_family_assigned_analyst, args=[FAMILY_GUID])
        _check_login(self, url)

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

        self.assertListEqual(response_json.keys(), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['assignedAnalyst']['email'], 'test_user@test.com')
        self.assertEqual(response_json[FAMILY_GUID]['assignedAnalyst']['fullName'], 'Test User')

        # unassign analyst
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json.keys(), [FAMILY_GUID])
        self.assertIsNone(response_json[FAMILY_GUID]['assignedAnalyst'])

    def test_update_success_story_types(self):
        url = reverse(update_family_fields_handler, args=[FAMILY_GUID])
        _check_login(self, url)

        # send valid request
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'successStoryTypes': ['O', 'D']}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json[FAMILY_GUID]['successStoryTypes'], ['O', 'D'])

    def test_receive_families_table_handler(self):
        url = reverse(receive_families_table_handler, args=[PROJECT_GUID])
        _check_login(self, url)

        # send request with a "families" attribute
        data = b'Family ID	Display Name	Description	Coded Phenotype\n\
"1"	"1"	"sf"	"LEFT VENTRICULAR NONCOMPACTION 10; LVNC10"\n\
"2"	"2"	"sz test"	""'

        f = SimpleUploadedFile("1000_genomes demo_families.tsv", data)

        response = self.client.post(url, {'f': f})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['info', 'errors', 'warnings', 'uploadedFileId'])

        url = reverse(edit_families_handler, args=[PROJECT_GUID])

        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'uploadedFileId': response_json['uploadedFileId']}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['familiesByGuid'])
