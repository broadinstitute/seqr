from __future__ import unicode_literals

import json

from django.urls.base import reverse

from seqr.models import AnalysisGroup
from seqr.views.apis.analysis_group_api import update_analysis_group_handler, delete_analysis_group_handler
from seqr.views.utils.test_utils import AuthenticationTestCase

PROJECT_GUID = 'R0001_1kg'


class AnalysisGroupAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    def test_create_update_and_delete_analysis_group(self):
        create_analysis_group_url = reverse(update_analysis_group_handler, args=[PROJECT_GUID])
        self.check_manager_login(create_analysis_group_url)

        # send invalid requests to create analysis_group
        response = self.client.post(create_analysis_group_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Missing required field(s): Name, Families')

        response = self.client.post(create_analysis_group_url, content_type='application/json', data=json.dumps({
            'name': 'new_analysis_group', 'familyGuids': ['fake_family_guid'],
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'The following families do not exist: fake_family_guid')

        # send valid request to create analysis_group
        response = self.client.post(create_analysis_group_url, content_type='application/json', data=json.dumps({
            'name': 'new_analysis_group', 'familyGuids': ['F000001_1', 'F000002_2']
        }))
        self.assertEqual(response.status_code, 200)
        new_analysis_group_response = response.json()
        self.assertEqual(len(new_analysis_group_response['analysisGroupsByGuid']), 1)
        new_analysis_group = next(iter(new_analysis_group_response['analysisGroupsByGuid'].values()))
        self.assertEqual(new_analysis_group['name'], 'new_analysis_group')
        self.assertSetEqual({'F000001_1', 'F000002_2'}, set(new_analysis_group['familyGuids']))

        guid = new_analysis_group['analysisGroupGuid']
        new_analysis_group_model = AnalysisGroup.objects.filter(guid=guid).first()
        self.assertIsNotNone(new_analysis_group_model)
        self.assertEqual(new_analysis_group_model.name, new_analysis_group['name'])

        self.assertEqual(new_analysis_group_model.families.count(), 2)
        self.assertSetEqual({'F000001_1', 'F000002_2'}, {family.guid for family in new_analysis_group_model.families.all()})

        # update the analysis_group
        update_analysis_group_url = reverse(update_analysis_group_handler, args=[PROJECT_GUID, guid])
        response = self.client.post(update_analysis_group_url, content_type='application/json',  data=json.dumps(
            {'name': 'updated_analysis_group', 'description': 'a description', 'familyGuids': ['F000001_1', 'F000003_3']}))

        self.assertEqual(response.status_code, 200)
        updated_analysis_group_response = response.json()
        self.assertEqual(len(updated_analysis_group_response['analysisGroupsByGuid']), 1)
        updated_analysis_group = next(iter(updated_analysis_group_response['analysisGroupsByGuid'].values()))
        self.assertEqual(updated_analysis_group['name'], 'updated_analysis_group')
        self.assertEqual(updated_analysis_group['description'], 'a description')
        self.assertSetEqual({'F000001_1', 'F000003_3'}, set(updated_analysis_group['familyGuids']))

        updated_analysis_group_model = AnalysisGroup.objects.filter(guid=guid).first()
        self.assertIsNotNone(updated_analysis_group_model)
        self.assertEqual(updated_analysis_group_model.name, updated_analysis_group['name'])
        self.assertEqual(updated_analysis_group_model.description, updated_analysis_group['description'])
        self.assertSetEqual({'F000001_1', 'F000003_3'}, {family.guid for family in updated_analysis_group_model.families.all()})

        # delete the analysis_group
        delete_analysis_group_url = reverse(delete_analysis_group_handler, args=[PROJECT_GUID, guid])
        response = self.client.post(delete_analysis_group_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'analysisGroupsByGuid': {guid: None}})

        # check that analysis_group was deleted
        new_analysis_group = AnalysisGroup.objects.filter(guid=guid)
        self.assertEqual(len(new_analysis_group), 0)
