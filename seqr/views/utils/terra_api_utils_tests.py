import json
import mock
import responses

from datetime import datetime
from django.test import TestCase
from django.contrib.auth.models import User

from seqr.views.utils.test_utils import TEST_TERRA_API_ROOT_URL, GOOGLE_TOKEN_RESULT,\
    GOOGLE_ACCESS_TOKEN_URL, TOKEN_AUTH_TIME, REGISTER_RESPONSE, TEST_SERVICE_ACCOUNT, TEST_OAUTH2_KEY
from seqr.views.utils.terra_api_utils import list_anvil_workspaces, user_get_workspace_acl,\
    anvil_call, user_get_workspace_access_level, TerraNotFoundException, TerraAPIException, \
    TerraRefreshTokenFailedException,  is_anvil_authenticated, is_google_authenticated, remove_token, \
    add_service_account, has_service_account_access, get_anvil_group_members, user_get_anvil_groups

GET_WORKSPACE_PATH = 'api/workspaces?fields=public,workspace.name,workspace.namespace'
AUTH_EXTRA_DATA = {"expires": 3599, "auth_time": TOKEN_AUTH_TIME, "token_type": "Bearer", "access_token": "ya29.EXAMPLE"}
LIST_WORKSPACE_RESPONSE = '[{"accessLevel": "PROJECT_OWNER", "public": false, "workspace": {"attributes": {"description": "Workspace for seqr project"}, "authorizationDomain": [], "bucketName": "fc-237998e6-663d-40b9-bd13-57c3bb6ac593", "createdBy": "test1@test.com", "createdDate": "2020-09-09T15:10:32.816Z", "isLocked": false, "lastModified": "2020-09-09T15:10:32.818Z", "name": "1000 Genomes Demo", "namespace": "my-seqr-billing", "workflowCollectionName": "237998e6-663d-40b9-bd13-57c3bb6ac593", "workspaceId": "237998e6-663d-40b9-bd13-57c3bb6ac593" }, "workspaceSubmissionStats": {"runningSubmissionsCount": 0}},\
{"accessLevel": "READER","public": true, "workspace": {"attributes": {"tag:tags": {"itemsType": "AttributeValue","items": ["differential-expression","tutorial"]},"description": "[DEGenome](https://github.com/eweitz/degenome) transforms differential expression data into inputs for [exploratory genome analysis with Ideogram.js](https://eweitz.github.io/ideogram/differential-expression?annots-url=https://www.googleapis.com/storage/v1/b/degenome/o/GLDS-4_array_differential_expression_ideogram_annots.json).  \\n\\nTry the [Notebook tutorial](https://app.terra.bio/#workspaces/degenome/degenome/notebooks/launch/degenome-tutorial.ipynb), where you can step through using DEGenome to analyze expression for mice flown in space!"},"authorizationDomain": [],"bucketName": "fc-2706d493-5fce-4fb2-9993-457c30364a06","createdBy": "test2@test.com","createdDate": "2020-01-14T10:21:14.575Z","isLocked": false,"lastModified": "2020-02-01T13:28:27.309Z","name": "degenome","namespace": "degenome","workflowCollectionName": "2706d493-5fce-4fb2-9993-457c30364a06","workspaceId": "2706d493-5fce-4fb2-9993-457c30364a06"},"workspaceSubmissionStats": {"runningSubmissionsCount": 0}},\
{"accessLevel": "PROJECT_OWNER","public": false, "workspace": {"attributes": {"description": "A workspace for seqr project"},"authorizationDomain": [],"bucketName": "fc-6a048145-c134-4004-a009-42824f826ee8","createdBy": "test3@test.com","createdDate": "2020-09-09T15:12:30.142Z","isLocked": false,"lastModified": "2020-09-09T15:12:30.145Z","name": "seqr-project 1000 Genomes Demo","namespace": "my-seqr-billing","workflowCollectionName": "6a048145-c134-4004-a009-42824f826ee8","workspaceId": "6a048145-c134-4004-a009-42824f826ee8"},"workspaceSubmissionStats": {"runningSubmissionsCount": 0}}]'
USERS_GROUP = 'TGG_USERS'

class TerraApiUtilsHelpersCase(TestCase):
    fixtures = ['users', 'social_auth']

    @mock.patch('seqr.views.utils.terra_api_utils.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
    def test_is_google_authenticated(self, mock_social_auth_key):
        user = User.objects.get(username='test_user')
        r = is_google_authenticated(user)
        self.assertTrue(r)

        remove_token(user)
        r = is_google_authenticated(user)
        self.assertTrue(r)

        local_user = User.objects.get(username='test_local_user')
        r = is_google_authenticated(local_user)
        self.assertFalse(r)

        mock_social_auth_key.__bool__.return_value = False
        r = is_google_authenticated(user)
        self.assertFalse(r)

    @mock.patch('seqr.views.utils.terra_api_utils.TERRA_API_ROOT_URL')
    @mock.patch('seqr.views.utils.terra_api_utils.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
    def test_is_anvil_authenticated(self, mock_social_auth_key, mock_terra_url):
        mock_social_auth_key.__bool__.return_value = False
        mock_terra_url.__bool__.return_value = True
        user = User.objects.get(username='test_user')
        r = is_anvil_authenticated(user)
        self.assertFalse(r)

        mock_social_auth_key.__bool__.return_value = True
        mock_terra_url.__bool__.return_value = False
        r = is_anvil_authenticated(user)
        self.assertFalse(r)

        mock_terra_url.__bool__.return_value = True
        r = is_anvil_authenticated(user)
        self.assertTrue(r)

        remove_token(user)
        r = is_anvil_authenticated(user)
        self.assertFalse(r)

@mock.patch('seqr.views.utils.terra_api_utils.SERVICE_ACCOUNT_FOR_ANVIL', TEST_SERVICE_ACCOUNT)
@mock.patch('seqr.views.utils.terra_api_utils.TERRA_API_ROOT_URL', TEST_TERRA_API_ROOT_URL)
@mock.patch('seqr.views.utils.terra_api_utils.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', TEST_OAUTH2_KEY)
@mock.patch('seqr.views.utils.terra_api_utils.time.time', lambda: AUTH_EXTRA_DATA['auth_time'] + 10)
class TerraApiUtilsCallsCase(TestCase):
    fixtures = ['users', 'social_auth']

    @responses.activate
    @mock.patch('seqr.views.utils.terra_api_utils.logger')
    def test_anvil_call(self, mock_logger):
        url = '{}register'.format(TEST_TERRA_API_ROOT_URL)
        responses.add(responses.GET, url, status=200, body=REGISTER_RESPONSE)
        r = anvil_call('get', 'register', 'ya.EXAMPLE')
        self.assertDictEqual(r['userInfo'], {"userEmail": "test@test.com", "userSubjectId": "123456"})
        mock_logger.info.assert_called_with('GET https://terra.api/register 200 127', None)
        self.assertEqual(len(mock_logger.method_calls), 1)

        mock_logger.reset_mock()
        responses.replace(responses.GET, url, status=404, body='{"causes": [], "message": "google subject Id 123456 not found in sam", "source": "sam", "stackTrace": [], "statusCode": 404, "timestamp": 1605282720182}')
        with self.assertRaises(TerraNotFoundException) as te:
            _ = anvil_call('get', 'register', 'ya.EXAMPLE')
        self.assertEqual(str(te.exception), 'None called Terra API: GET /register got status 404 with reason: Not Found')
        self.assertEqual(len(mock_logger.method_calls), 0)

    @responses.activate
    @mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
    @mock.patch('seqr.views.utils.terra_api_utils.logger')
    def test_list_workspaces(self, mock_logger, mock_redis):
        user = User.objects.get(username='test_user')

        url = '{}{}'.format(TEST_TERRA_API_ROOT_URL, GET_WORKSPACE_PATH)
        mock_redis.return_value.get.return_value = None
        responses.add(responses.GET, url, status=200,
            body = '[{"public": false, "workspace": {"name": "1000 Genomes Demo", "namespace": "my-seqr-billing" }},' +
                   '{"public": true,"workspace": {"name": "degenome","namespace": "degenome"}},' +
                   '{"public": false,"workspace": {"name": "seqr-project 1000 Genomes Demo","namespace": "my-seqr-billing"}}]')
        workspaces = list_anvil_workspaces(user)
        self.assertEqual(len(workspaces), 2)
        self.assertEqual(workspaces[1]['workspace']['namespace'], 'my-seqr-billing')
        mock_logger.info.assert_called_with('GET https://terra.api/api/workspaces?fields=public,workspace.name,workspace.namespace 200 276', user)
        self.assertEqual(len(mock_logger.method_calls), 1)
        responses.assert_call_count(url, 1)
        mock_redis.return_value.set.assert_called_with(
            'terra_req__test_user__api/workspaces?fields=public,workspace.name,workspace.namespace', json.dumps(workspaces))
        mock_redis.return_value.expire.assert_called_with(
            'terra_req__test_user__api/workspaces?fields=public,workspace.name,workspace.namespace', 300)

        mock_logger.reset_mock()
        responses.reset()
        mock_redis.return_value.get.return_value = '[{"workspace": {"name": "1000 Genomes Demo", "namespace": "my-seqr-billing" }},' +\
                   '{"workspace": {"name": "seqr-project 1000 Genomes Demo","namespace": "my-seqr-billing"}}]'
        workspaces = list_anvil_workspaces(user)
        self.assertEqual(len(workspaces), 2)
        self.assertEqual(workspaces[1]['workspace']['namespace'], 'my-seqr-billing')
        mock_logger.info.assert_called_with('Terra API cache hit for: GET {} {}'.format(GET_WORKSPACE_PATH, user), user)
        mock_redis.return_value.get.assert_called_with('terra_req__{}__{}'.format(user, GET_WORKSPACE_PATH))
        responses.assert_call_count(url, 0)  # no call to the Terra API

        mock_logger.reset_mock()
        mock_redis.return_value.get.return_value = None
        responses.add(responses.GET, url, status=401)
        with self.assertRaises(TerraAPIException) as ec:
            _ = list_anvil_workspaces(user)
        self.assertEqual(str(ec.exception),
            'Error: called Terra API: GET /api/workspaces?fields=public,workspace.name,workspace.namespace got status: 401 with a reason: Unauthorized')

    @responses.activate
    @mock.patch('seqr.views.utils.terra_api_utils.logger')
    @mock.patch('seqr.views.utils.terra_api_utils.anvil_call')
    def test_refresh_token(self, mock_anvil_call, mock_logger):
        user = User.objects.get(username='test_user')

        with mock.patch('seqr.views.utils.terra_api_utils.time.time') as mock_time:
            mock_time.return_value = AUTH_EXTRA_DATA['auth_time'] + 60*60 + 10
            responses.add(responses.POST, GOOGLE_ACCESS_TOKEN_URL, status = 401)
            with self.assertRaises(TerraRefreshTokenFailedException) as te:
                _ = list_anvil_workspaces(user)
            self.assertEqual(str(te.exception),
                'Refresh token failed. 401 Client Error: Unauthorized for url: https://accounts.google.com/o/oauth2/token')
            self.assertEqual(te.exception.status_code, 401)
            mock_logger.warning.assert_called_with(
                'Refresh token failed. 401 Client Error: Unauthorized for url: https://accounts.google.com/o/oauth2/token',
                user)
            self.assertEqual(mock_logger.warning.call_count, 1)
            mock_logger.info.assert_called_with('Refreshing access token', user)
            self.assertEqual(mock_logger.info.call_count, 1)

            mock_logger.reset_mock()
            responses.replace(responses.POST, GOOGLE_ACCESS_TOKEN_URL, status=200, body=GOOGLE_TOKEN_RESULT)
            list_anvil_workspaces(user)
            mock_logger.warning.assert_not_called()
            mock_logger.info.assert_called_with('Refreshing access token', user)
            self.assertEqual(mock_logger.info.call_count, 1)
            self.assertEqual(mock_anvil_call.call_count, 1)
            self.assertEqual(mock_anvil_call.call_args.args[2], 'ya29.c.EXAMPLE')

    @responses.activate
    @mock.patch('seqr.views.utils.terra_api_utils.logger')
    def test_get_workspace_acl(self, mock_logger):
        user = User.objects.get(username='test_user')

        url = '{}api/workspaces/my-seqr-billing/my-seqr-workspace/acl'.format(TEST_TERRA_API_ROOT_URL)
        responses.add(responses.GET, url, status=200, body='{"acl": {"test1@test1.com": {"accessLevel": "OWNER","canCompute": true,"canShare": true,"pending": false},"sf-seqr@my-seqr.iam.gserviceaccount.com": {"accessLevel": "OWNER","canCompute": true,"canShare": true,"pending": false},"test2@test2.org": {"accessLevel": "OWNER","canCompute": true,"canShare": true,"pending": false},"test3@test3.com": {"accessLevel": "READER","canCompute": false,"canShare": false,"pending": false}}}')
        acl = user_get_workspace_acl(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertIn('test3@test3.com', acl.keys())
        mock_logger.info.assert_called_with(
            'GET https://terra.api/api/workspaces/my-seqr-billing/my-seqr-workspace/acl 200 425', user)
        self.assertEqual(len(mock_logger.method_calls), 1)

        mock_logger.reset_mock()
        responses.replace(responses.GET, url, status=401)
        r = user_get_workspace_acl(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertDictEqual(r, {})

        mock_logger.warning.assert_called_with(
            'Error: called Terra API: GET /api/workspaces/my-seqr-billing/my-seqr-workspace/acl got status: 401 with a reason: Unauthorized', user)
        self.assertEqual(len(mock_logger.method_calls), 1)

        mock_logger.reset_mock()
        responses.replace(responses.GET, url, status=403)
        r = user_get_workspace_acl(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertDictEqual(r, {})
        mock_logger.warning.assert_called_with(
            'test_user got access denied (403) from Terra API: GET /api/workspaces/my-seqr-billing/my-seqr-workspace/acl with reason: Forbidden', user)
        self.assertEqual(len(mock_logger.method_calls), 1)

        mock_logger.reset_mock()
        responses.replace(responses.GET, url, status=404)
        r = user_get_workspace_acl(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertDictEqual(r, {})
        mock_logger.warning.assert_called_with(
            'test_user called Terra API: GET /api/workspaces/my-seqr-billing/my-seqr-workspace/acl got status 404 with reason: Not Found', user)
        self.assertEqual(len(mock_logger.method_calls), 1)

    @responses.activate
    @mock.patch('seqr.views.utils.terra_api_utils.logger')
    @mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
    def test_user_get_workspace_access_level(self, mock_redis, mock_logger):
        user = User.objects.get(username='test_user')

        mock_redis.return_value.get.return_value = None
        url = '{}api/workspaces/my-seqr-billing/my-seqr-workspace?fields=accessLevel,canShare'.format(TEST_TERRA_API_ROOT_URL)
        responses.add(responses.GET, url, status=200, body='{"accessLevel": "OWNER"}')
        permission = user_get_workspace_access_level(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertDictEqual(permission, {"accessLevel": "OWNER"})
        mock_logger.info.assert_called_with(
            'GET https://terra.api/api/workspaces/my-seqr-billing/my-seqr-workspace?fields=accessLevel,canShare 200 24', user)
        self.assertEqual(len(mock_logger.method_calls), 1)
        responses.assert_call_count(url, 1)
        mock_redis.return_value.set.assert_called_with(
            'terra_req__test_user__api/workspaces/my-seqr-billing/my-seqr-workspace?fields=accessLevel,canShare',
            json.dumps(permission))
        mock_redis.return_value.expire.assert_called_with(
            'terra_req__test_user__api/workspaces/my-seqr-billing/my-seqr-workspace?fields=accessLevel,canShare', 60)

        mock_logger.reset_mock()
        responses.replace(responses.GET, url, status=404)
        permission = user_get_workspace_access_level(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertDictEqual(permission, {})
        responses.assert_call_count(url, 2)

        # Test cache hit
        mock_redis.return_value.get.return_value = '{"accessLevel": "READER"}'
        permission = user_get_workspace_access_level(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertDictEqual(permission, {"accessLevel": "READER"})
        mock_redis.return_value.get.assert_called_with(
            'terra_req__test_user__api/workspaces/my-seqr-billing/my-seqr-workspace?fields=accessLevel,canShare')
        responses.assert_call_count(url, 2)  # No API called since the call_count is kept unchanged.

    @responses.activate
    def test_add_service_account(self):
        user = User.objects.get(username='test_user')

        url = '{}api/workspaces/my-seqr-billing/my-seqr-workspace/acl'.format(TEST_TERRA_API_ROOT_URL)
        responses.add(responses.GET, url, status=200, body='{{"acl": {{"{}": {{"accessLevel": "READER","canCompute": false,"canShare": false,"pending": false}} }} }}'.format(TEST_SERVICE_ACCOUNT))
        r = add_service_account(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertFalse(r)
        self.assertEqual(responses.calls[0].request.url, url)
        responses.assert_call_count(url, 1)

        responses.reset()
        responses.add(responses.GET, url, status=200, body='{"acl": {}}')
        responses.add(responses.PATCH, url, status=200, body='{{"usersUpdated": [{{"email": "{}" }}]}}'.format(TEST_SERVICE_ACCOUNT))
        r = add_service_account(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertTrue(r)
        responses.assert_call_count(url, 2)
        self.assertEqual(responses.calls[0].request.method, responses.GET)
        self.assertEqual(responses.calls[1].request.method, responses.PATCH)
        self.assertEqual(responses.calls[1].request.body, '[{"email": "test_account@my-seqr.iam.gserviceaccount.com", "accessLevel": "READER", "canShare": false, "canCompute": false}]')

        responses.replace(responses.PATCH, url, status=200, body='{"usersUpdated": []}')
        with self.assertRaises(TerraAPIException) as te:
            _ = add_service_account(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertEqual(str(te.exception), 'Failed to grant seqr service account access to the workspace my-seqr-billing/my-seqr-workspace')

    @responses.activate
    def test_has_service_account(self):
        user = User.objects.get(username='test_user')

        url = '{}api/workspaces/my-seqr-billing/my-seqr-workspace/acl'.format(TEST_TERRA_API_ROOT_URL)
        responses.add(responses.GET, url, status=200,
                      body='{{"acl": {{"{}": {{"accessLevel": "READER","canCompute": false,"canShare": false,"pending": false}} }} }}'.format(
                          TEST_SERVICE_ACCOUNT))
        r = has_service_account_access(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertTrue(r)

        responses.replace(responses.GET, url, status=200,
                      body='{{"acl": {{"{}": {{"accessLevel": "READER","canCompute": false,"canShare": false,"pending": true}} }} }}'.format(
                          TEST_SERVICE_ACCOUNT))
        r = has_service_account_access(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertFalse(r)

        responses.replace(responses.GET, url, status=200,
                      body='{"acl": {"other_user": {"accessLevel": "READER","canCompute": false,"canShare": false,"pending": false} } }')
        r = has_service_account_access(user, 'my-seqr-billing', 'my-seqr-workspace')
        self.assertFalse(r)

    @responses.activate
    @mock.patch('seqr.views.utils.terra_api_utils.SERVICE_ACCOUNT_CREDENTIALS')
    @mock.patch('seqr.views.utils.terra_api_utils.datetime')
    @mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
    @mock.patch('seqr.views.utils.terra_api_utils.logger')
    def test_get_anvil_group_members(self, mock_logger, mock_redis, mock_datetime, mock_credentials):
        user = User.objects.get(username='test_user')

        url = '{}{}'.format(TEST_TERRA_API_ROOT_URL, 'api/groups/TGG_USERS')
        responses.add(responses.GET, url, status=200, body=json.dumps({
            'adminsEmails': ['test_user@broadinstitute.org'],
            'groupEmail': 'TGG_USERS@firecloud.org',
            'membersEmails': ['test@test.com', TEST_SERVICE_ACCOUNT]
        }))
        mock_redis.return_value.get.return_value = None
        members = get_anvil_group_members(user, USERS_GROUP)
        self.assertListEqual(members, ['test_user@broadinstitute.org', 'test@test.com'])
        mock_logger.info.assert_called_with('GET https://terra.api/api/groups/TGG_USERS 200 175', user)
        self.assertEqual(len(mock_logger.method_calls), 1)
        responses.assert_call_count(url, 1)
        self.assertEqual(responses.calls[0].request.headers['Authorization'], 'Bearer ya29.EXAMPLE')
        mock_redis.return_value.get.assert_called_with('terra_req__test_user__api/groups/TGG_USERS')
        mock_redis.return_value.set.assert_called_with(
            'terra_req__test_user__api/groups/TGG_USERS', json.dumps(members))
        mock_redis.return_value.expire.assert_called_with('terra_req__test_user__api/groups/TGG_USERS', 300)

        # test with service account credentials
        mock_datetime.now.return_value = datetime(2021, 1, 1)
        mock_credentials.expiry = datetime(2021, 1, 2)
        mock_credentials.token = 'ya29.SA_EXAMPLE'
        get_anvil_group_members(user, USERS_GROUP, use_sa_credentials=True)
        self.assertEqual(responses.calls[1].request.headers['Authorization'], 'Bearer ya29.SA_EXAMPLE')
        mock_credentials.refresh.assert_not_called()
        mock_redis.return_value.get.assert_called_with('terra_req__SA__api/groups/TGG_USERS')
        mock_redis.return_value.set.assert_called_with('terra_req__SA__api/groups/TGG_USERS', json.dumps(members))
        mock_redis.return_value.expire.assert_called_with('terra_req__SA__api/groups/TGG_USERS', 300)

        mock_credentials.expiry = datetime(2021, 1, 1)
        get_anvil_group_members(user, USERS_GROUP, use_sa_credentials=True)
        mock_credentials.refresh.assert_called_once()

        responses.add(responses.GET, url, status=401)
        self.assertDictEqual(get_anvil_group_members(user, USERS_GROUP), {})
        mock_logger.warning.assert_called_with(
            'Error: called Terra API: GET /api/groups/TGG_USERS got status: 401 with a reason: Unauthorized', user)

        responses.reset()
        cached_members = ['test@other_test.com']
        mock_redis.return_value.get.return_value = json.dumps(cached_members)
        members = get_anvil_group_members(user, USERS_GROUP)
        self.assertListEqual(members, cached_members)
        mock_logger.info.assert_called_with('Terra API cache hit for: GET api/groups/TGG_USERS test_user', user)
        mock_redis.return_value.get.assert_called_with('terra_req__test_user__api/groups/TGG_USERS')
        responses.assert_call_count(url, 0)  # no call to the Terra API

    @responses.activate
    @mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
    @mock.patch('seqr.views.utils.terra_api_utils.logger')
    def test_user_get_anvil_groups(self, mock_logger, mock_redis):
        user = User.objects.get(username='test_user')

        url = f'{TEST_TERRA_API_ROOT_URL}api/groups'
        mock_redis.return_value.get.return_value = None
        responses.add(responses.GET, url, status=200, body=json.dumps([
            {'groupEmail': 'TGG_Users@firecloud.org', 'groupName': 'TGG_Users', 'role': 'Admin'},
            {'groupEmail': 'External_Users@firecloud.org', 'groupName': 'External_Users', 'role': 'Member'},
        ]))
        groups = user_get_anvil_groups(user)
        self.assertListEqual(groups, ['TGG_Users', 'External_Users'])
        mock_logger.info.assert_called_with('GET https://terra.api/api/groups 200 183', user)
        self.assertEqual(len(mock_logger.method_calls), 1)
        responses.assert_call_count(url, 1)
        mock_redis.return_value.set.assert_called_with('terra_req__test_user__api/groups', json.dumps(groups))
        mock_redis.return_value.expire.assert_called_with('terra_req__test_user__api/groups', 300)

        mock_redis.return_value.get.return_value = None
        responses.add(responses.GET, url, status=401)
        with self.assertRaises(TerraAPIException) as ec:
            user_get_anvil_groups(user)
        self.assertEqual(str(ec.exception),
            'Error: called Terra API: GET /api/groups got status: 401 with a reason: Unauthorized')

        responses.reset()
        cached_groups = ['foo', 'bar', 'baz']
        mock_redis.return_value.get.return_value = json.dumps(cached_groups)
        groups = user_get_anvil_groups(user)
        self.assertListEqual(groups, cached_groups)
        mock_logger.info.assert_called_with('Terra API cache hit for: GET api/groups test_user', user)
        mock_redis.return_value.get.assert_called_with('terra_req__test_user__api/groups')
        responses.assert_call_count(url, 0)  # no call to the Terra API
