import json
import mock

from django.urls.base import reverse

from seqr.models import AnalysisGroup, DynamicAnalysisGroup
from seqr.views.apis.analysis_group_api import update_analysis_group_handler, delete_analysis_group_handler, \
    update_dynamic_analysis_group_handler, delete_dynamic_analysis_group_handler
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase

PROJECT_GUID = 'R0001_1kg'


class AnalysisGroupAPITest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
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

        response = self.client.post(create_analysis_group_url, content_type='application/json', data=json.dumps({
            'name': 'new_analysis_group', 'familyGuids': ['F000001_1'], 'workspaceName': 'foo',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Both Workspace Name and Workspace Namespace are required to add access control')

        # send valid request to create analysis_group
        response = self.client.post(create_analysis_group_url, content_type='application/json', data=json.dumps({
            'name': 'new_analysis_group', 'familyGuids': ['F000001_1', 'F000002_2'], 'uploadedFamilyIds': {
                'info': ["Uploaded 2 families"], 'parsedData': [['F000001_1'], ['F000002_2']],
            },
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

        # re-creating the analysis group fails
        response = self.client.post(create_analysis_group_url, content_type='application/json', data=json.dumps({
            'name': 'new_analysis_group', 'familyGuids': ['F000001_1', 'F000002_2']
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'An analysis group named "new_analysis_group" already exists for project "1kg project n\xe5me with uni\xe7\xf8de"')

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

        # updating workspace fields are correctly permissioned
        body = {
            'name': 'updated_analysis_group', 'description': 'access control group', 'familyGuids': ['F000001_1', 'F000003_3'],
            'workspaceName': 'test', 'workspaceNamespace': 'my-seqr-billing',
        }
        response = self.client.post(update_analysis_group_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)
        updated_analysis_group_model = AnalysisGroup.objects.get(guid=guid)
        self.assertIsNone(updated_analysis_group_model.workspace_name)
        self.assertEqual(updated_analysis_group_model.description, updated_analysis_group['description'])

        self.login_pm_user()
        response = self.client.post(update_analysis_group_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)

        body['workspaceName'] = 'anvil-no-project-workspace2'
        response = self.client.post(update_analysis_group_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        updated_analysis_group_response = response.json()
        self.assertEqual(len(updated_analysis_group_response['analysisGroupsByGuid']), 1)
        self.assertDictEqual(next(iter(updated_analysis_group_response['analysisGroupsByGuid'].values())), {
            'name': 'updated_analysis_group',
            'description': 'access control group',
            'analysisGroupGuid': guid,
            'projectGuid': PROJECT_GUID,
            'familyGuids': ['F000001_1', 'F000003_3'],
            'workspaceNamespace': 'my-seqr-billing',
            'workspaceName': 'anvil-no-project-workspace2',
        })
        updated_analysis_group_model = AnalysisGroup.objects.get(guid=guid)
        self.assertEqual(updated_analysis_group_model.workspace_namespace, 'my-seqr-billing')
        self.assertEqual(updated_analysis_group_model.workspace_name, 'anvil-no-project-workspace2')
        self.login_manager()

        # delete the analysis_group
        delete_analysis_group_url = reverse(delete_analysis_group_handler, args=[PROJECT_GUID, guid])
        response = self.client.post(delete_analysis_group_url, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Unable to delete access control group')

        updated_analysis_group_model.workspace_namespace = None
        updated_analysis_group_model.workspace_name = None
        updated_analysis_group_model.save()

        response = self.client.post(delete_analysis_group_url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'analysisGroupsByGuid': {guid: None}})

        # check that analysis_group was deleted
        new_analysis_group = AnalysisGroup.objects.filter(guid=guid)
        self.assertEqual(len(new_analysis_group), 0)

    def test_create_update_and_delete_dynamic_analysis_group(self):
        create_analysis_group_url = reverse(update_dynamic_analysis_group_handler, args=[PROJECT_GUID])
        self.check_manager_login(create_analysis_group_url)

        # send invalid requests to create analysis_group
        response = self.client.post(create_analysis_group_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Missing required field(s): Name, Criteria')

        # send valid request to create analysis_group
        response = self.client.post(create_analysis_group_url, content_type='application/json', data=json.dumps({
            'name': 'new_dynamic_group', 'criteria': {'analysisStatus': ['Q']},
        }))
        self.assertEqual(response.status_code, 200)
        new_analysis_group_response = response.json()
        self.assertEqual(len(new_analysis_group_response['analysisGroupsByGuid']), 1)
        new_analysis_group = next(iter(new_analysis_group_response['analysisGroupsByGuid'].values()))
        self.assertEqual(new_analysis_group['name'], 'new_dynamic_group')

        guid = new_analysis_group['analysisGroupGuid']
        new_analysis_group_model = DynamicAnalysisGroup.objects.filter(guid=guid).first()
        self.assertIsNotNone(new_analysis_group_model)
        self.assertEqual(new_analysis_group_model.name, new_analysis_group['name'])

        # update the analysis_group
        update_analysis_group_url = reverse(update_dynamic_analysis_group_handler, args=[PROJECT_GUID, guid])
        response = self.client.post(update_analysis_group_url, content_type='application/json',  data=json.dumps(
            {**new_analysis_group, 'name': 'updated_analysis_group', 'criteria': {'analysisStatus': ['I']}}))

        self.assertEqual(response.status_code, 200)
        updated_analysis_group_response = response.json()
        self.assertEqual(len(updated_analysis_group_response['analysisGroupsByGuid']), 1)
        updated_analysis_group = next(iter(updated_analysis_group_response['analysisGroupsByGuid'].values()))
        self.assertEqual(updated_analysis_group['name'], 'updated_analysis_group')
        self.assertDictEqual(updated_analysis_group['criteria'], {'analysisStatus': ['I']})

        updated_analysis_group_model = DynamicAnalysisGroup.objects.filter(guid=guid).first()
        self.assertIsNotNone(updated_analysis_group_model)
        self.assertEqual(updated_analysis_group_model.name, updated_analysis_group['name'])
        self.assertEqual(updated_analysis_group_model.criteria, updated_analysis_group['criteria'])

        # delete the analysis_group
        delete_analysis_group_url = reverse(delete_dynamic_analysis_group_handler, args=[PROJECT_GUID, guid])
        response = self.client.post(delete_analysis_group_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'analysisGroupsByGuid': {guid: None}})

        # check that analysis_group was deleted
        new_analysis_group = DynamicAnalysisGroup.objects.filter(guid=guid)
        self.assertEqual(len(new_analysis_group), 0)
