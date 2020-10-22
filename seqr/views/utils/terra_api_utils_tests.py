import mock
import responses

from django.test import TestCase
from django.contrib.auth.models import User

from seqr.views.utils.terra_api_utils import get_anvil_billing_projects, get_anvil_profile, _anvil_session_store,\
    list_anvil_workspaces, get_anvil_workspace_acl
from settings import TERRA_API_ROOT_URL

GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'


class TerraApiUtilsCase(TestCase):
    fixtures = ['users']

    @responses.activate
    def setUp(self):
        content = b'{"access_token":"ya29.c.EXAMPLE","expires_in":3599,"token_type":"Bearer"}'
        responses.add(responses.POST, GOOGLE_TOKEN_URL, status = 200, body = content)
        self.user = User.objects.get(email='test_user@test.com')
        _ = _anvil_session_store.get_session(self.user)  # Create a session before testing

    @responses.activate
    def test_get_billing_projects(self):
        url = TERRA_API_ROOT_URL + 'api/profile/billing'
        responses.add(responses.GET, url, status = 200, body = '[{"creationStatus": "Ready","projectName": "my-seqr-billing","role": "Owner"}]')

        billing_projects = get_anvil_billing_projects(self.user)
        self.assertEqual(len(billing_projects), 1)
        self.assertEqual(billing_projects[0]['projectName'], 'my-seqr-billing')

        responses.replace(responses.GET, url, status = 401)
        with self.assertRaises(Exception) as ec:
            _ = get_anvil_billing_projects(self.user)
        self.assertEqual(str(ec.exception),
            'Error: called Terra API "api/profile/billing" got status: 401 with a reason: Unauthorized')

    @responses.activate
    def test_get_anvil_profile(self):
        url = TERRA_API_ROOT_URL + 'register'
        responses.add(responses.GET, url, status = 200, body = '{"enabled":{"ldap":true,"allUsersGroup":true,"google":true},"userInfo": {"userEmail":"sf-seqr@my-seqr.iam.gserviceaccount.com","userSubjectId":"108344681601016521986"}}')

        profile = get_anvil_profile(self.user)
        self.assertDictEqual(profile, {'enabled': {'ldap': True, 'allUsersGroup': True, 'google': True},
            'userInfo': {'userEmail': 'sf-seqr@my-seqr.iam.gserviceaccount.com', 'userSubjectId': '108344681601016521986'}})

        responses.replace(responses.GET, url, status = 404)
        with self.assertRaises(Exception) as ec:
            _ = get_anvil_profile(self.user)
        self.assertEqual(str(ec.exception),
            'Error: called Terra API "register" got status: {} with a reason: {}'.format(404, 'Not Found'))

    @responses.activate
    def test_list_workspaces(self):
        url = TERRA_API_ROOT_URL + 'api/workspaces'
        responses.add(responses.GET, url, status = 200,
            body = '[{"accessLevel": "PROJECT_OWNER", "public": false, "workspace": {"attributes": {"description": "Workspace for seqr project"}, "authorizationDomain": [], "bucketName": "fc-237998e6-663d-40b9-bd13-57c3bb6ac593", "createdBy": "test1@test.com", "createdDate": "2020-09-09T15:10:32.816Z", "isLocked": false, "lastModified": "2020-09-09T15:10:32.818Z", "name": "1000 Genomes Demo", "namespace": "my-seqr-billing", "workflowCollectionName": "237998e6-663d-40b9-bd13-57c3bb6ac593", "workspaceId": "237998e6-663d-40b9-bd13-57c3bb6ac593" }, "workspaceSubmissionStats": {"runningSubmissionsCount": 0}},'
                   '{"accessLevel": "READER","public": true,"workspace": {"attributes": {"tag:tags": {"itemsType": "AttributeValue","items": ["differential-expression","tutorial"]},"description": "[DEGenome](https://github.com/eweitz/degenome) transforms differential expression data into inputs for [exploratory genome analysis with Ideogram.js](https://eweitz.github.io/ideogram/differential-expression?annots-url=https://www.googleapis.com/storage/v1/b/degenome/o/GLDS-4_array_differential_expression_ideogram_annots.json).  \\n\\nTry the [Notebook tutorial](https://app.terra.bio/#workspaces/degenome/degenome/notebooks/launch/degenome-tutorial.ipynb), where you can step through using DEGenome to analyze expression for mice flown in space!"},"authorizationDomain": [],"bucketName": "fc-2706d493-5fce-4fb2-9993-457c30364a06","createdBy": "test2@test.com","createdDate": "2020-01-14T10:21:14.575Z","isLocked": false,"lastModified": "2020-02-01T13:28:27.309Z","name": "degenome","namespace": "degenome","workflowCollectionName": "2706d493-5fce-4fb2-9993-457c30364a06","workspaceId": "2706d493-5fce-4fb2-9993-457c30364a06"},"workspaceSubmissionStats": {"runningSubmissionsCount": 0}},'
                   '{"accessLevel": "PROJECT_OWNER","public": false,"workspace": {"attributes": {"description": "A workspace for seqr project"},"authorizationDomain": [],"bucketName": "fc-6a048145-c134-4004-a009-42824f826ee8","createdBy": "test3@test.com","createdDate": "2020-09-09T15:12:30.142Z","isLocked": false,"lastModified": "2020-09-09T15:12:30.145Z","name": "seqr-project 1000 Genomes Demo","namespace": "my-seqr-billing","workflowCollectionName": "6a048145-c134-4004-a009-42824f826ee8","workspaceId": "6a048145-c134-4004-a009-42824f826ee8"},"workspaceSubmissionStats": {"runningSubmissionsCount": 0}}]')
        workspaces = list_anvil_workspaces(self.user)
        self.assertEqual(len(workspaces), 3)
        self.assertDictEqual(workspaces[0], {"accessLevel": "PROJECT_OWNER", "public": False, "workspace": {"attributes": {"description": "Workspace for seqr project"}, "authorizationDomain": [], "bucketName": "fc-237998e6-663d-40b9-bd13-57c3bb6ac593", "createdBy": "test1@test.com", "createdDate": "2020-09-09T15:10:32.816Z", "isLocked": False, "lastModified": "2020-09-09T15:10:32.818Z", "name": "1000 Genomes Demo", "namespace": "my-seqr-billing", "workflowCollectionName": "237998e6-663d-40b9-bd13-57c3bb6ac593", "workspaceId": "237998e6-663d-40b9-bd13-57c3bb6ac593" }, "workspaceSubmissionStats": {"runningSubmissionsCount": 0}})

        responses.replace(responses.GET, url, status = 200,
            body = '[{"accessLevel": "PROJECT_OWNER", "workspace": {"name": "1000 Genomes Demo", "namespace": "my-seqr-billing", "workspaceId": "237998e6-663d-40b9-bd13-57c3bb6ac593" }},'
                   '{"accessLevel": "READER","workspace": {"name": "degenome","namespace": "degenome", "workspaceId": "2706d493-5fce-4fb2-9993-457c30364a06"}},'
                   '{"accessLevel": "PROJECT_OWNER","workspace": {"name": "seqr-project 1000 Genomes Demo","namespace": "my-seqr-billing","workspaceId": "6a048145-c134-4004-a009-42824f826ee8"}}]')
        workspaces = list_anvil_workspaces(self.user,
            fields='accessLevel,workspace.name,workspace.namespace,workspace.workspaceId')
        self.assertNotIn('public', workspaces[0].keys())

        responses.replace(responses.GET, url, status = 401)
        with self.assertRaises(Exception) as ec:
            _ = list_anvil_workspaces(self.user,
            fields = 'accessLevel,workspace.name,workspace.namespace,workspace.workspaceId')
        self.assertEqual(str(ec.exception),
            'Error: called Terra API "api/workspaces" got status: {} with a reason: {}'.format(401, 'Unauthorized'))

    @responses.activate
    def test_get_workspace_acl(self):
        url = TERRA_API_ROOT_URL + 'api/workspaces/my-seqr-billing/my-seqr-workspace/acl'
        responses.add(responses.GET, url, status = 200, body = '{"acl": {"test1@test1.com": {"accessLevel": "OWNER","canCompute": true,"canShare": true,"pending": false},"sf-seqr@my-seqr.iam.gserviceaccount.com": {"accessLevel": "OWNER","canCompute": true,"canShare": true,"pending": false},"test2@test2.org": {"accessLevel": "OWNER","canCompute": true,"canShare": true,"pending": false},"test3@test3.com": {"accessLevel": "READER","canCompute": false,"canShare": false,"pending": false}}}')
        acl = get_anvil_workspace_acl('my-seqr-billing', 'my-seqr-workspace')
        self.assertIn('test3@test3.com', acl.keys())

        responses.replace(responses.GET, url, status = 401)
        with self.assertRaises(Exception) as ec:
            _ = get_anvil_workspace_acl('my-seqr-billing', 'my-seqr-workspace')
        self.assertEqual(str(ec.exception),
            'Error: called Terra API "api/workspaces/my-seqr-billing/my-seqr-workspace/acl"'
            ' got status: {} with a reason: {}'.format(401, 'Unauthorized'))
