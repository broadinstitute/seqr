# -*- coding: utf-8 -*-
import json
import mock
from datetime import datetime
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls.base import reverse

from seqr.views.apis.family_api import update_family_pedigree_image, update_family_assigned_analyst, \
    update_family_fields_handler, update_family_analysed_by, edit_families_handler, delete_families_handler, \
    receive_families_table_handler, create_family_note, update_family_note, delete_family_note
from seqr.views.utils.test_utils import AuthenticationTestCase, FAMILY_NOTE_FIELDS

FAMILY_GUID = 'F000001_1'
FAMILY_GUID2 = 'F000002_2'

PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'
PM_REQUIRED_PROJECT_GUID = 'R0003_test'

FAMILY_ID_FIELD = 'familyId'
PREVIOUS_FAMILY_ID_FIELD = 'previousFamilyId'


class FamilyAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    def test_edit_families_handler(self, mock_pm_group):
        url = reverse(edit_families_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

        # send invalid request
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, "'families' not specified")

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

        # Test PM permission
        url = reverse(edit_families_handler, args=[PM_REQUIRED_PROJECT_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'families': [{'familyGuid': 'F000012_12'}]}))
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    def test_delete_families_handler(self, mock_pm_group):
        url = reverse(delete_families_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

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

        # Test PM permission
        url = reverse(delete_families_handler, args=[PM_REQUIRED_PROJECT_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'families': [{'familyGuid': 'F000012_12'}]}))
        self.assertEqual(response.status_code, 200)

    def test_update_family_analysed_by(self):
        url = reverse(update_family_analysed_by, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        # send request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertEqual(response_json[FAMILY_GUID]['analysedBy'][0]['createdBy']['fullName'], 'Test Collaborator User')

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
        self.assertEqual(response_json[FAMILY_GUID]['assignedAnalyst']['email'], 'seqr+test_user@populationgenomics.org.au')
        self.assertEqual(response_json[FAMILY_GUID]['assignedAnalyst']['fullName'], 'Test User')

        # unassign analyst
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), [FAMILY_GUID])
        self.assertIsNone(response_json[FAMILY_GUID]['assignedAnalyst'])

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    def test_update_success_story_types(self, mock_analyst_group):
        url = reverse(update_family_fields_handler, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'successStoryTypes': ['O', 'D']}))
        self.assertEqual(response.status_code, 403)

        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'

        # send valid request
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'successStoryTypes': ['O', 'D']}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(response_json[FAMILY_GUID]['successStoryTypes'], ['O', 'D'])

    @mock.patch('seqr.views.utils.json_to_orm_utils.timezone.now', lambda: datetime.strptime('2020-01-01', '%Y-%m-%d'))
    def test_update_family_fields(self):
        url = reverse(update_family_fields_handler, args=[FAMILY_GUID])
        self.check_collaborator_login(url)

        body = {FAMILY_ID_FIELD: 'new_id', 'description': 'Updated description', 'analysis_status': 'C'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json[FAMILY_GUID]['description'], 'Updated description')
        self.assertEqual(response_json[FAMILY_GUID][FAMILY_ID_FIELD], '1')
        self.assertEqual(response_json[FAMILY_GUID]['analysisStatus'], 'C')
        self.assertEqual(response_json[FAMILY_GUID]['analysisStatusLastModifiedBy'], 'Test Collaborator User')
        self.assertEqual(response_json[FAMILY_GUID]['analysisStatusLastModifiedDate'], '2020-01-01T00:00:00')

        # Do not update audit fields if value does not change
        self.login_manager()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[FAMILY_GUID]['analysisStatusLastModifiedBy'], 'Test Collaborator User')

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    def test_receive_families_table_handler(self, mock_pm_group):
        url = reverse(receive_families_table_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

        # send invalid request
        data = b'Description	Coded Phenotype\n\
        "family one description"	""\n\
        "family two description"	""'
        response = self.client.post(url, {'f': SimpleUploadedFile("1000_genomes demo_families.tsv", data)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid header, missing family id column')
        self.assertDictEqual(response.json(), {
            'errors': ['Invalid header, missing family id column'], 'warnings': []})

        data = b'Family ID	Previous Family ID	Display Name	Description	Coded Phenotype\n\
        "1_renamed"	"1_old"	"1"	"family one description"	""\n\
        "2"	""	"2"	"family two description"	""'
        response = self.client.post(url, {'f': SimpleUploadedFile("1000_genomes demo_families.tsv", data)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid input')
        self.assertDictEqual(response.json(), {
            'errors': ['Could not find families with the following previous IDs: 1_old'], 'warnings': []})

        # send valid request
        data = b'Family ID	Previous Family ID	Display Name	Description	Coded Phenotype\n\
"1_renamed"	"1"	"1"	"family one description"	""\n\
"2"	""	"2"	"family two description"	""'

        response = self.client.post(url, {'f': SimpleUploadedFile("1000_genomes demo_families.tsv", data)})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings', 'uploadedFileId'})

        url = reverse(edit_families_handler, args=[PROJECT_GUID])

        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'uploadedFileId': response_json['uploadedFileId']}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(list(response_json.keys()), ['familiesByGuid'])
        self.assertSetEqual(set(response_json['familiesByGuid'].keys()), {FAMILY_GUID2, FAMILY_GUID})
        family_1 = response_json['familiesByGuid'][FAMILY_GUID]
        self.assertEqual(family_1['description'], 'family one description')
        self.assertEqual(family_1['familyId'], '1_renamed')
        family_2 = response_json['familiesByGuid'][FAMILY_GUID2]
        self.assertEqual(family_2['description'], 'family two description')
        self.assertEqual(family_2['familyId'], '2')

        # Test PM permission
        url = reverse(receive_families_table_handler, args=[PM_REQUIRED_PROJECT_GUID])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'

        response = self.client.post(url, {'f': SimpleUploadedFile('families.tsv', 'Family ID\n1'.encode('utf-8'))})
        self.assertEqual(response.status_code, 200)

    def test_create_update_and_delete_family_note(self):
        # create the note
        create_note_url = reverse(create_family_note, args=[FAMILY_GUID])
        self.check_collaborator_login(create_note_url)

        response = self.client.post(create_note_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Missing required field(s): note, noteType'})

        response = self.client.post(create_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new analysis note', 'noteType': 'A'}
        ))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'familyNotesByGuid'})
        self.assertEqual(len(response_json['familyNotesByGuid']), 1)
        new_note_guid = list(response_json['familyNotesByGuid'].keys())[0]
        new_note_response = list(response_json['familyNotesByGuid'].values())[0]
        self.assertSetEqual(set(new_note_response.keys()), FAMILY_NOTE_FIELDS)
        self.assertEqual(new_note_response['noteGuid'], new_note_guid)
        self.assertEqual(new_note_response['note'], 'new analysis note')
        self.assertEqual(new_note_response['noteType'], 'A')
        self.assertEqual(new_note_response['createdBy'], 'Test Collaborator User')

        # update the note
        update_note_url = reverse(update_family_note, args=[FAMILY_GUID, new_note_guid])
        response = self.client.post(update_note_url, content_type='application/json',  data=json.dumps(
            {'note': 'updated note'}))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json, {'familyNotesByGuid': {new_note_guid: mock.ANY}})
        updated_note_response = response_json['familyNotesByGuid'][new_note_guid]
        self.assertEqual(updated_note_response['note'], 'updated note')

        # test other users cannot modify the note
        self.login_manager()
        response = self.client.post(update_note_url, content_type='application/json', data=json.dumps(
            {'note': 'further updated note'}))
        self.assertEqual(response.status_code, 403)

        # delete the gene_note
        delete_note_url = reverse(delete_family_note, args=[FAMILY_GUID, new_note_guid])

        response = self.client.post(delete_note_url, content_type='application/json')
        self.assertEqual(response.status_code, 403)

        self.login_collaborator()
        response = self.client.post(delete_note_url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'familyNotesByGuid': {new_note_guid: None}})
