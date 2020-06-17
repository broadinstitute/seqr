# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls.base import reverse

from seqr.views.apis.family_api import update_family_pedigree_image, update_family_assigned_analyst, \
    update_family_fields_handler, update_family_analysed_by, edit_families_handler, delete_families_handler, receive_families_table_handler
from seqr.views.utils.test_utils import AuthenticationTestCase

FAMILY_GUID = 'F000001_1'
FAMILY_GUID2 = 'F000002_2'

PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'

FAMILY_ID_FIELD = 'familyId'
PREVIOUS_FAMILY_ID_FIELD = 'previousFamilyId'


class FamilyAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    def test_edit_families_handler(self):
        url = reverse(edit_families_handler, args=[PROJECT_GUID])
        self.check_staff_login(url)

        # send request with a "families" attribute
        req_values = {
            'families': [
                {'familyGuid': FAMILY_GUID, 'description': 'Test description 1'},
                {PREVIOUS_FAMILY_ID_FIELD: '2', FAMILY_ID_FIELD: '22', 'description': 'Test description 2'},
                {FAMILY_ID_FIELD: 'new_family', 'description': 'Test descriptions for a new family'}
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
        new_guids = set(response_json['familiesByGuid'].keys()) - set([FAMILY_GUID, 'F000002_2'])
        new_guid = new_guids.pop()
        self.assertEqual(response_json['familiesByGuid'][new_guid]['description'], 'Test descriptions for a new family')

    def test_delete_families_handler(self):
        url = reverse(delete_families_handler, args=[PROJECT_GUID])
        self.check_staff_login(url)

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
        self.assertSetEqual(set(response_json.keys()), {'individualsByGuid', 'familiesByGuid'})
        self.assertIsNone(response_json['familiesByGuid'][FAMILY_GUID])
        self.assertIsNone(response_json['familiesByGuid'][FAMILY_GUID2])

        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'families': None}))
        self.assertEqual(response.status_code, 400)

    def test_update_family_analysed_by(self):
        url = reverse(update_family_analysed_by, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        # send request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['analysedBy'][0]['createdBy']['fullName'], 'Test Non Staff User')

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
        self.assertEqual(response_json[FAMILY_GUID]['assignedAnalyst']['email'], 'test_user@test.com')
        self.assertEqual(response_json[FAMILY_GUID]['assignedAnalyst']['fullName'], 'Test User')

        # unassign analyst
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertIsNone(response_json[FAMILY_GUID]['assignedAnalyst'])

    def test_update_success_story_types(self):
        url = reverse(update_family_fields_handler, args=[FAMILY_GUID])
        self.check_manager_login(url)

        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'successStoryTypes': ['O', 'D']}))
        self.assertEqual(response.status_code, 403)
        self.login_staff_user()

        # send valid request
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'successStoryTypes': ['O', 'D']}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json[FAMILY_GUID]['successStoryTypes'], ['O', 'D'])

    def test_receive_families_table_handler(self):
        url = reverse(receive_families_table_handler, args=[PROJECT_GUID])
        self.check_staff_login(url)

        # send request with a "families" attribute
        data = b'Family ID	Display Name	Description	Coded Phenotype\n\
"1"	"1"	"family one description"	""\n\
"2"	"2"	"family two description"	""'

        f = SimpleUploadedFile("1000_genomes demo_families.tsv", data)

        response = self.client.post(url, {'f': f})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(list(response_json.keys())), {'info', 'errors', 'warnings', 'uploadedFileId'})

        url = reverse(edit_families_handler, args=[PROJECT_GUID])

        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'uploadedFileId': response_json['uploadedFileId']}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), ['familiesByGuid'])
        self.assertSetEqual(set(list(response_json['familiesByGuid'].keys())), {FAMILY_GUID2, FAMILY_GUID})
        self.assertEqual(response_json['familiesByGuid'][FAMILY_GUID]['description'], 'family one description')
        self.assertEqual(response_json['familiesByGuid'][FAMILY_GUID2]['description'], 'family two description')
