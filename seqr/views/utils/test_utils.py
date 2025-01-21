# Utilities used for unit and integration tests.
from collections import defaultdict
from copy import deepcopy
from django.contrib.auth.models import User, Group
from django.test import TestCase
from guardian.shortcuts import assign_perm
from io import StringIO
import json
import logging
import mock
import re
import requests
import responses
from urllib.parse import quote_plus, urlparse

from seqr.models import Project, CAN_VIEW, CAN_EDIT

WINDOW_REGEX_TEMPLATE = 'window\.{key}=(?P<value>[^)<]+)'


class AuthenticationTestCase(TestCase):
    databases = '__all__'
    SUPERUSER = 'superuser'
    ANALYST = 'analyst'
    PM = 'project_manager'
    DATA_MANAGER = 'data_manager'
    MANAGER = 'manager'
    COLLABORATOR = 'collaborator'
    AUTHENTICATED_USER = 'authenticated'
    NO_POLICY_USER = 'no_policy'

    ES_HOSTNAME = 'testhost'
    MOCK_AIRTABLE_KEY = ''

    super_user = None
    analyst_user = None
    pm_user = None
    data_manager_user = None
    manager_user = None
    collaborator_user = None
    no_access_user = None
    inactive_user = None
    no_policy_user = None

    def setUp(self):
        patcher = mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', self.ES_HOSTNAME)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_API_KEY', self.MOCK_AIRTABLE_KEY)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.SEQR_PRIVACY_VERSION', 2.1)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.SEQR_TOS_VERSION', 1.3)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
        self.mock_analyst_group = patcher.start()
        self.mock_analyst_group.__str__.return_value = 'Analysts'
        self.mock_analyst_group.__eq__.side_effect = lambda s: str(self.mock_analyst_group) == s
        self.mock_analyst_group.__bool__.side_effect = lambda: bool(str(self.mock_analyst_group))
        self.mock_analyst_group.resolve_expression.return_value = 'analysts'
        self.addCleanup(patcher.stop)

        self._log_stream = StringIO()
        logging.getLogger().handlers[0].stream = self._log_stream

    @classmethod
    def setUpTestData(cls):
        cls.super_user = User.objects.get(username='test_superuser')
        cls.analyst_user = User.objects.get(username='test_user')
        cls.pm_user = User.objects.get(username='test_pm_user')
        cls.data_manager_user = User.objects.get(username='test_data_manager')
        cls.manager_user = User.objects.get(username='test_user_manager')
        cls.collaborator_user = User.objects.get(username='test_user_collaborator')
        cls.no_access_user = User.objects.get(username='test_user_no_access')
        cls.inactive_user = User.objects.get(username='test_user_inactive')
        cls.no_policy_user = User.objects.get(username='test_user_no_policies')
        cls.local_user = User.objects.get(username='test_local_user')

        edit_group = Group.objects.get(pk=2)
        view_group = Group.objects.get(pk=3)
        edit_group.user_set.add(cls.manager_user)
        view_group.user_set.add(cls.manager_user, cls.collaborator_user)
        assign_perm(user_or_group=edit_group, perm=CAN_EDIT, obj=Project.objects.filter(can_edit_group=edit_group))
        assign_perm(user_or_group=edit_group, perm=CAN_VIEW, obj=Project.objects.filter(can_view_group=edit_group))
        assign_perm(user_or_group=view_group, perm=CAN_VIEW, obj=Project.objects.filter(can_view_group=view_group))

        cls.add_additional_user_groups()

    @classmethod
    def add_additional_user_groups(cls):
        analyst_group = Group.objects.get(pk=4)
        analyst_group.user_set.add(cls.analyst_user, cls.pm_user)
        assign_perm(user_or_group=analyst_group, perm=CAN_EDIT, obj=Project.objects.filter(id__in=[1, 2, 3]))
        assign_perm(user_or_group=analyst_group, perm=CAN_VIEW, obj=Project.objects.filter(id__in=[1, 2, 3]))

        pm_group = Group.objects.get(pk=5)
        pm_group.user_set.add(cls.pm_user)

    def check_require_login(self, url, **request_kwargs):
        self._check_login(url, self.AUTHENTICATED_USER, **request_kwargs)

    def check_require_login_no_policies(self, url, **request_kwargs):
        self._check_login(url, self.NO_POLICY_USER, **request_kwargs)

    def check_collaborator_login(self, url, **request_kwargs):
        self._check_login(url, self.COLLABORATOR, **request_kwargs)

    def check_manager_login(self, url, **request_kwargs):
        return self._check_login(url, self.MANAGER, **request_kwargs)

    def check_analyst_login(self, url):
        self._check_login(url, self.ANALYST)

    def check_pm_login(self, url):
        self._check_login(url, self.PM)

    def check_data_manager_login(self, url):
        self._check_login(url, self.DATA_MANAGER)

    def check_superuser_login(self, url, **request_kwargs):
        self._check_login(url, self.SUPERUSER, **request_kwargs)

    def login_base_user(self):
        self.client.force_login(self.no_access_user)

    def login_collaborator(self):
        self.client.force_login(self.collaborator_user)

    def login_manager(self):
        self.client.force_login(self.manager_user)

    def login_analyst_user(self):
        self.client.force_login(self.analyst_user)

    def login_pm_user(self):
        self.client.force_login(self.pm_user)

    def login_data_manager_user(self):
        self.client.force_login(self.data_manager_user)

    def _check_login(self, url, permission_level, request_data=None, login_redirect_url='/api/login-required-error',
                     policy_redirect_url='/api/policy-required-error', permission_denied_error=403):
        """For integration tests of django views that can only be accessed by a logged-in user,
        the 1st step is to authenticate. This function checks that the given url redirects requests
        if the user isn't logged-in, and then authenticates a test user.

        Args:
            test_case (object): the django.TestCase or unittest.TestCase object
            url (string): The url of the django view being tested.
            permission_level (string): what level of permission this url requires
         """
        # check that it redirects if you don't login
        parsed_url = urlparse(url)
        next_query = quote_plus('?{}'.format(parsed_url.query)) if parsed_url.query else ''
        next_url = 'next={}{}'.format('/'.join(map(quote_plus, parsed_url.path.split('/'))), next_query)
        login_required_url = '{}?{}'.format(login_redirect_url, next_url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, login_required_url)

        self.client.force_login(self.inactive_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.client.force_login(self.no_policy_user)
        if permission_level == self.NO_POLICY_USER:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '{}?{}'.format(policy_redirect_url, next_url))

        self.client.force_login(self.no_access_user)
        if permission_level == self.AUTHENTICATED_USER:
            return

        # check that users without view permission users can't access collaborator URLs
        if permission_level == self.COLLABORATOR:
            if request_data:
                response = self.client.post(url, content_type='application/json', data=json.dumps(request_data))
            else:
                response = self.client.get(url)
            self.assertEqual(response.status_code, permission_denied_error)

        self.login_collaborator()
        if permission_level == self.COLLABORATOR:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.client.force_login(self.manager_user)
        if permission_level == self.MANAGER:
            return response

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.login_analyst_user()
        if permission_level in self.ANALYST:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.login_pm_user()
        if permission_level in self.PM:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.login_data_manager_user()
        if permission_level in self.DATA_MANAGER:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.client.force_login(self.super_user)

    def get_initial_page_window(self, key, response):
        content = response.content.decode('utf-8')
        regex = WINDOW_REGEX_TEMPLATE.format(key=key)
        self.assertRegex(content, regex)
        m = re.search(regex, content)
        return json.loads(m.group('value'))

    def get_initial_page_json(self, response):
        return self.get_initial_page_window('initialJSON', response)

    def check_no_analyst_no_access(self, url, get_response=None, has_override=False):
        self.mock_analyst_group.__str__.return_value = ''

        response = get_response() if get_response else self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        self.client.force_login(self.super_user)
        response = get_response() if get_response else self.client.get(url)
        self.assertEqual(response.status_code, 200 if has_override else 403)
        return response

    def reset_logs(self):
        self._log_stream.truncate(0)
        self._log_stream.seek(0)

    def assert_json_logs(self, user, expected, offset=0):
        logs = self._log_stream.getvalue().split('\n')
        if offset:
            logs = logs[offset:]
        for i, (message, extra) in enumerate(expected):
            extra = extra or {}
            validate = extra.pop('validate', None)
            log_value = json.loads(logs[i])
            expected_log = {
                'timestamp': mock.ANY, 'severity': 'INFO', **extra,
            }
            if user:
                expected_log['user'] = user.email
            if message is not None:
                expected_log['message'] = message
            self.assertDictEqual(log_value, expected_log)
            if validate:
                validate(log_value)

    def assert_no_logs(self):
        self.assertEqual(self._log_stream.getvalue(), '')

TEST_WORKSPACE_NAMESPACE = 'my-seqr-billing'
TEST_WORKSPACE_NAME = 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de'
TEST_WORKSPACE_NAME1 = 'anvil-project 1000 Genomes Demo'
TEST_EMPTY_PROJECT_WORKSPACE = 'empty'
TEST_NO_PROJECT_WORKSPACE_NAME = 'anvil-no-project-workspace1'
TEST_NO_PROJECT_WORKSPACE_NAME2 = 'anvil-no-project-workspace2'
EXT_WORKSPACE_NAMESPACE = 'ext-data'
EXT_WORKSPACE_NAME = 'anvil-non-analyst-project 1000 Genomes Demo'

TEST_SERVICE_ACCOUNT = 'test_account@my-seqr.iam.gserviceaccount.com'

ANVIL_WORKSPACES = [{
    'workspace_namespace': TEST_WORKSPACE_NAMESPACE,
    'workspace_name': TEST_WORKSPACE_NAME,
    'public': False,
    'acl': {
        'Test_User_Manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        'test_user_collaborator@test.com': {
            "accessLevel": "READER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        TEST_SERVICE_ACCOUNT: {
            "accessLevel": "READER",
            "pending": False,
            "canShare": False,
            "canCompute": True
        },
        'test_user_not_registered@test.com': {
            "accessLevel": "READER",
            "pending": True,
            "canShare": False,
            "canCompute": True
        },
        'Analysts@firecloud.org': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": False,
            "canCompute": False
        },
        'test_user_pure_anvil@test.com': {
            "accessLevel": "READER",
            "pending": False,
            "canShare": False,
            "canCompute": True
        }
    },
    'workspace': {
        'bucketName': 'test_bucket'
    },
}, {
    'workspace_namespace': TEST_WORKSPACE_NAMESPACE,
    'workspace_name': TEST_WORKSPACE_NAME1,
    'public': False,
    'acl': {
        'test_user_manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        'test_user_collaborator@test.com': {
            "accessLevel": "READER",
            "pending": False,
            "canShare": False,
            "canCompute": False
        },
        'Analysts@firecloud.org': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": False,
            "canCompute": False
        },
    },
    'workspace': {
        'bucketName': 'test_bucket'
    },
}, {
    'workspace_namespace': TEST_WORKSPACE_NAMESPACE,
    'workspace_name': TEST_NO_PROJECT_WORKSPACE_NAME,
    'public': True,
    'acl': {
        'test_user_manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        'test_user_collaborator@test.com': {
            "accessLevel": "READER",
            "pending": False,
            "canShare": False,
            "canCompute": True
        },
    },
    'workspace': {
        'authorizationDomain': [],
        'bucketName': 'test_bucket'
    },
}, {
    'workspace_namespace': EXT_WORKSPACE_NAMESPACE,
    'workspace_name': TEST_EMPTY_PROJECT_WORKSPACE,
    'public': False,
    'acl': {
        'Analysts@firecloud.org': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": False,
            "canCompute": False
        },
        'test_user_manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
    },
}, {
    'workspace_namespace': TEST_WORKSPACE_NAMESPACE,
    'workspace_name': TEST_NO_PROJECT_WORKSPACE_NAME2,
    'public': False,
    'acl': {
        'test_user_manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        'test_pm_user@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": False,
            "canCompute": False
        },
    },
    'workspace': {
        'authorizationDomain': [{'membersGroupName': 'AUTH_restricted_group'}],
        'bucketName': 'test_bucket'
    },
}, {
    'workspace_namespace': EXT_WORKSPACE_NAMESPACE,
    'workspace_name': EXT_WORKSPACE_NAME,
    'public': True,
    'acl': {
        'test_user_manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
    },
    'workspace': {
        'authorizationDomain': [],
        'bucketName': 'test_bucket'
    },
},
]


ANVIL_GROUPS = {
    'project-managers': ['test_pm_user@test.com'],
    'Analysts': ['test_pm_user@test.com', 'test_user@broadinstitute.org'],
}
ANVIL_GROUP_LOOKUP = defaultdict(list)
for group, users in ANVIL_GROUPS.items():
    for user in users:
        ANVIL_GROUP_LOOKUP[user].append(group)


TEST_TERRA_API_ROOT_URL =  'https://terra.api/'
TEST_OAUTH2_PROVIDER = 'google-oauth2'

# the time must the same as that in 'auth_time' in the social_auth fixture data
TOKEN_AUTH_TIME = 1603287741
REGISTER_RESPONSE = '{"enabled":{"ldap":true,"allUsersGroup":true,"google":true},"userInfo": {"userEmail":"test@test.com","userSubjectId":"123456"}}'


def get_ws_acl_side_effect(user, workspace_namespace, workspace_name):
    wss = filter(lambda x: x['workspace_namespace'] == workspace_namespace and x['workspace_name'] == workspace_name, ANVIL_WORKSPACES)
    wss = list(wss)
    return wss[0]['acl'] if wss else {}


def get_ws_al_side_effect(user, workspace_namespace, workspace_name, meta_fields=None):
    wss = filter(lambda x: x['workspace_namespace'] == workspace_namespace and x['workspace_name'] == workspace_name, ANVIL_WORKSPACES)
    wss = list(wss)
    acl = wss[0]['acl'] if wss else {}
    email = user.email.lower()
    user_acl = next((v for k, v in acl.items() if email == k.lower()), None)
    for user_group in ANVIL_GROUP_LOOKUP[email]:
        if not user_acl:
            user_acl = acl.get(f'{user_group}@firecloud.org')
    access_level = {
        'accessLevel': user_acl['accessLevel'],
        'canShare': user_acl['canShare'],
    } if user_acl else {}
    if meta_fields:
        access_level['workspace'] = {}
        if 'workspace.bucketName' in meta_fields:
            access_level['workspace']['bucketName'] = wss[0]['workspace']['bucketName']
        if meta_fields and 'workspace.authorizationDomain' in meta_fields:
            access_level['workspace']['authorizationDomain'] = wss[0]['workspace']['authorizationDomain']
    return access_level


def get_workspaces_side_effect(user):
    email = user.email.lower()
    return [
        {
            'public': ws['public'],
            'workspace':{
                'namespace': ws['workspace_namespace'],
                'name': ws['workspace_name']
            }
        } for ws in ANVIL_WORKSPACES if any(
            email == k.lower() or k.replace('@firecloud.org', '') in ANVIL_GROUP_LOOKUP[email]
            for k in ws['acl'].keys())
    ]



def get_groups_side_effect(user):
    return [group for group, users in ANVIL_GROUPS.items() if user.email in users]


def get_group_members_side_effect(user, group, use_sa_credentials=False):
    members = ANVIL_GROUPS[str(group)]
    if user.email in members or use_sa_credentials:
        return members
    return {}


class AnvilAuthenticationTestCase(AuthenticationTestCase):

    ES_HOSTNAME = ''
    MOCK_AIRTABLE_KEY = 'airflow_access'

    # mock the terra apis
    def setUp(self):
        patcher = mock.patch('seqr.views.utils.terra_api_utils.TERRA_API_ROOT_URL', TEST_TERRA_API_ROOT_URL)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.react_app.SOCIAL_AUTH_PROVIDER', TEST_OAUTH2_PROVIDER)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.terra_api_utils.SOCIAL_AUTH_PROVIDER', TEST_OAUTH2_PROVIDER)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.orm_to_json_utils.SERVICE_ACCOUNT_FOR_ANVIL', TEST_SERVICE_ACCOUNT)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.INTERNAL_NAMESPACES', ['my-seqr-billing'])
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.terra_api_utils.time')
        patcher.start().return_value = TOKEN_AUTH_TIME + 10
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.list_anvil_workspaces')
        self.mock_list_workspaces = patcher.start()
        self.mock_list_workspaces.side_effect = get_workspaces_side_effect
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.user_get_workspace_acl')
        self.mock_get_ws_acl = patcher.start()
        self.mock_get_ws_acl.side_effect = get_ws_acl_side_effect
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.user_get_workspace_access_level')
        self.mock_get_ws_access_level = patcher.start()
        self.mock_get_ws_access_level.side_effect = get_ws_al_side_effect
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.user_get_anvil_groups')
        self.mock_get_groups = patcher.start()
        self.mock_get_groups.side_effect = get_groups_side_effect
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.get_anvil_group_members')
        self.mock_get_group_members = patcher.start()
        self.mock_get_group_members.side_effect = get_group_members_side_effect
        self.addCleanup(patcher.stop)
        super(AnvilAuthenticationTestCase, self).setUp()

    @classmethod
    def add_additional_user_groups(cls):
        analyst_group = Group.objects.get(pk=4)
        analyst_group.user_set.add(cls.analyst_user, cls.pm_user)

    def assert_no_extra_anvil_calls(self):
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_groups.assert_not_called()
        self.mock_get_group_members.assert_not_called()



PROJECT_GUID = 'R0001_1kg'

class AirflowTestCase(AnvilAuthenticationTestCase):
    MOCK_AIRFLOW_URL = 'http://testairflowserver'
    ADDITIONAL_REQUEST_COUNT = 0
    DAG_NAME = 'LOADING_PIPELINE'

    def setUp(self):
        self._dag_url = f'{self.MOCK_AIRFLOW_URL}/api/v1/dags/{self.DAG_NAME}'
        self.set_up_one_dag()

        patcher = mock.patch('seqr.views.utils.airflow_utils.google.auth.default', lambda **kwargs: (None, None))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.airflow_utils.AuthorizedSession', mock.Mock(return_value=requests))
        self.mock_authorized_session = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.airflow_utils.AIRFLOW_WEBSERVER_URL', self.MOCK_AIRFLOW_URL)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.airflow_utils.safe_post_to_slack')
        self.mock_slack = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.airflow_utils.logger')
        self.mock_airflow_logger = patcher.start()
        self.addCleanup(patcher.stop)

        super().setUp()

    def set_up_one_dag(self, **kwargs):
        # check dag running state
        responses.add(responses.GET, f'{self._dag_url}/dagRuns', json={
            'dag_runs': [{
                'conf': {},
                'dag_id': 'seqr_vcf_to_es_AnVIL_WGS_v0.0.1',
                'dag_run_id': 'manual__2022-04-28T11:51:22.735124+00:00',
                'end_date': None, 'execution_date': '2022-04-28T11:51:22.735124+00:00',
                'external_trigger': True, 'start_date': '2022-04-28T11:51:25.626176+00:00',
                'state': 'success'}
            ]})
        # trigger dag
        responses.add(responses.POST, f'{self._dag_url}/dagRuns', json={})
        # update variables
        responses.add(
            responses.PATCH, f'{self.MOCK_AIRFLOW_URL}/api/v1/variables/{self.DAG_NAME}',
            json={'key': self.DAG_NAME, 'value': 'updated variables'},
        )
        # check for updated variables
        self._add_update_check_dag_responses(**kwargs)

    def _add_update_check_dag_responses(self, **kwargs):
        # get task id
        self._add_dag_tasks_response(['R0006_test'])
        # get task id again if the response of the previous request didn't include the updated guid
        self._add_dag_tasks_response([self.LOADING_PROJECT_GUID])
        # get task id again if the response of the previous request didn't include the updated guid
        self._add_dag_tasks_response([self.LOADING_PROJECT_GUID, PROJECT_GUID])

    def _add_dag_tasks_response(self, projects):
        tasks = []
        for project in projects:
            tasks += [
                {'task_id': 'create_dataproc_cluster'},
                {'task_id': f'pyspark_compute_project_{project}'},
                {'task_id': f'pyspark_compute_variants_{self.DAG_NAME}'},
                {'task_id': f'pyspark_export_project_{project}'},
                {'task_id': 'scale_dataproc_cluster'},
                {'task_id': f'skip_compute_project_subset_{project}'}
            ]
        responses.add(responses.GET, f'{self._dag_url}/tasks', json={
            'tasks': tasks, 'total_entries': len(tasks),
        })

    def set_dag_trigger_error_response(self, status=200):
        responses.replace(responses.GET, f'{self._dag_url}/dagRuns', status=status, json={'dag_runs': [{
            'conf': {},
            'dag_id': self.DAG_NAME,
            'dag_run_id': 'manual__2022-04-28T11:51:22.735124+00:00',
            'end_date': None, 'execution_date': '2022-04-28T11:51:22.735124+00:00',
            'external_trigger': True, 'start_date': '2022-04-28T11:51:25.626176+00:00',
            'state': 'running'}
        ]})

    def assert_airflow_loading_calls(self, trigger_error=False, additional_tasks_check=False, dataset_type=None, offset=0, **kwargs):
        call_count = 5
        if additional_tasks_check:
            call_count = 6
        if trigger_error:
            call_count = 1
        self._assert_call_counts(call_count)

        dag_variable_overrides = self._get_dag_variable_overrides(additional_tasks_check)
        dag_variables = {
            'projects_to_run': [dag_variable_overrides['project']] if 'project' in dag_variable_overrides else self.PROJECTS,
            'dataset_type': dataset_type or dag_variable_overrides['dataset_type'],
            'reference_genome': dag_variable_overrides.get('reference_genome', 'GRCh38'),
            'callset_path': f'gs://test_bucket/{dag_variable_overrides["callset_path"]}',
            'sample_type': dag_variable_overrides['sample_type'],
        }
        if dag_variable_overrides.get('skip_validation'):
            dag_variables['skip_validation'] = True
        dag_variables['sample_source'] = dag_variable_overrides['sample_source']
        self._assert_airflow_calls(dag_variables, call_count, offset=offset)

    def _assert_call_counts(self, call_count):
        self.mock_airflow_logger.info.assert_not_called()
        self.assertEqual(len(responses.calls), call_count + self.ADDITIONAL_REQUEST_COUNT)
        self.assertEqual(self.mock_authorized_session.call_count, call_count)

    def _assert_airflow_calls(self, dag_variables, call_count, offset=0):
        self._assert_dag_running_state_calls(offset)

        if call_count < 2:
            return

        self._assert_update_variables_airflow_calls(dag_variables, offset)
        self._assert_update_check_airflow_calls(call_count, offset, update_check_path=f'{self._dag_url}/tasks')
        call_cnt = call_count - 1

        # trigger dag
        self.assertEqual(responses.calls[offset+call_cnt].request.url, f'{self._dag_url}/dagRuns')
        self.assertEqual(responses.calls[offset+call_cnt].request.method, 'POST')
        self.assertDictEqual(json.loads(responses.calls[offset+call_cnt].request.body), {})

        self.mock_airflow_logger.warning.assert_not_called()
        self.mock_airflow_logger.error.assert_not_called()

    def _assert_dag_running_state_calls(self, offset):
        self.assertEqual(responses.calls[offset].request.url, f'{self._dag_url}/dagRuns')
        self.assertEqual(responses.calls[offset].request.method, "GET")

    def _assert_update_variables_airflow_calls(self, dag_variables, offset):
        self.assertEqual(responses.calls[offset+1].request.url, f'{self.MOCK_AIRFLOW_URL}/api/v1/variables/{self.DAG_NAME}')
        self.assertEqual(responses.calls[offset+1].request.method, 'PATCH')
        request_body = json.loads(responses.calls[offset + 1].request.body)
        self.assertEqual(request_body['key'], self.DAG_NAME)
        self.assertDictEqual(
            json.loads(request_body['value']),
            json.loads(json.dumps(dag_variables))
        )

    def _assert_update_check_airflow_calls(self, call_count, offset, update_check_path):
        self.assertEqual(responses.calls[offset + 2].request.url, update_check_path)
        self.assertEqual(responses.calls[offset + 2].request.method, 'GET')

        self.assertEqual(responses.calls[offset + 3].request.url, update_check_path)
        self.assertEqual(responses.calls[offset + 3].request.method, 'GET')

        if call_count > 5:
            self.assertEqual(responses.calls[offset + 4].request.url, update_check_path)
            self.assertEqual(responses.calls[offset + 4].request.method, 'GET')


    @staticmethod
    def _get_dag_variable_overrides(additional_tasks_check):
        raise NotImplementedError


@mock.patch('seqr.views.utils.terra_api_utils.SOCIAL_AUTH_PROVIDER', TEST_OAUTH2_PROVIDER)
class AirtableTest(object):

    def assert_expected_airtable_call(self, call_index, filter_formula, fields, additional_params=None):
        expected_params = {
            'fields[]': mock.ANY,
            'pageSize': '100',
            'filterByFormula': filter_formula,
        }
        if additional_params:
            expected_params.update(additional_params)
        self.assertDictEqual(responses.calls[call_index].request.params, expected_params)
        self.assertListEqual(self._get_list_param(responses.calls[call_index].request, 'fields%5B%5D'), fields)
        self.assert_expected_airtable_headers(call_index)

    def assert_expected_airtable_headers(self, call_index):
        self.assertEqual(responses.calls[call_index].request.headers['Authorization'], f'Bearer {self.MOCK_AIRTABLE_KEY}')

    @staticmethod
    def _get_list_param(call, param):
        query_params = call.url.split('?')[1].split('&')
        param_str = f'{param}='
        return [p.replace(param_str, '') for p in query_params if p.startswith(param_str)]


USER_FIELDS = {
    'dateJoined', 'email', 'firstName', 'lastLogin', 'lastName', 'username', 'displayName', 'id',  'isActive', 'isAnvil',
    'isAnalyst', 'isDataManager', 'isPm', 'isSuperuser',
}
PROJECT_FIELDS = {
    'projectGuid', 'projectCategoryGuids', 'canEdit', 'name', 'description', 'createdDate', 'lastModifiedDate',
    'lastAccessedDate',  'mmeContactUrl', 'genomeVersion', 'mmePrimaryDataOwner', 'mmeContactInstitution',
    'isMmeEnabled', 'workspaceName', 'workspaceNamespace', 'hasCaseReview', 'enableHgmd', 'isDemo', 'allUserDemo',
    'userIsCreator', 'consentCode', 'isAnalystProject', 'vlmContactEmail',
}

ANALYSIS_GROUP_FIELDS = {'analysisGroupGuid', 'description', 'name', 'projectGuid', 'familyGuids'}
DYNAMIC_ANALYSIS_GROUP_FIELDS = {'analysisGroupGuid', 'criteria', 'name', 'projectGuid'}

SUMMARY_FAMILY_FIELDS = {
    'projectGuid', 'familyGuid', 'analysedBy', 'familyId', 'displayName', 'description',
    'analysisStatus', 'createdDate', 'assignedAnalyst', 'codedPhenotype', 'mondoId',
}
FAMILY_FIELDS = {
    'pedigreeImage', 'postDiscoveryOmimNumbers',
    'pedigreeDataset', 'analysisStatusLastModifiedDate', 'analysisStatusLastModifiedBy', 'mondoId',
}
FAMILY_FIELDS.update(SUMMARY_FAMILY_FIELDS)
CASE_REVIEW_FAMILY_FIELDS = {
    'caseReviewNotes', 'caseReviewSummary'
}
INTERNAL_FAMILY_FIELDS = {
    'individualGuids', 'successStory', 'successStoryTypes', 'pubmedIds', 'externalData', 'postDiscoveryMondoId'
}
INTERNAL_FAMILY_FIELDS.update(FAMILY_FIELDS)

FAMILY_NOTE_FIELDS = {'noteGuid', 'note', 'noteType', 'lastModifiedDate', 'createdBy', 'familyGuid'}


INDIVIDUAL_CORE_FIELDS = {
    'individualGuid', 'individualId', 'sex', 'affected', 'displayName', 'notes', 'createdDate', 'lastModifiedDate',
    'popPlatformFilters', 'filterFlags', 'population', 'birthYear', 'deathYear',
    'onsetAge', 'maternalEthnicity', 'paternalEthnicity', 'consanguinity', 'affectedRelatives', 'expectedInheritance',
    'disorders', 'candidateGenes', 'rejectedGenes', 'arFertilityMeds', 'arIui', 'arIvf', 'arIcsi', 'arSurrogacy',
    'arDonoregg', 'arDonorsperm', 'svFlags',
}

INDIVIDUAL_FIELDS = {
    'projectGuid', 'familyGuid', 'paternalId', 'maternalId', 'paternalGuid', 'maternalGuid',
    'features', 'absentFeatures', 'nonstandardFeatures', 'absentNonstandardFeatures',
}
INDIVIDUAL_FIELDS.update(INDIVIDUAL_CORE_FIELDS)

CASE_REVIEW_INDIVIDUAL_FIELDS = {
    'caseReviewStatus', 'caseReviewDiscussion', 'caseReviewStatusLastModifiedDate', 'caseReviewStatusLastModifiedBy',
}
CORE_INTERNAL_INDIVIDUAL_FIELDS = {
    'probandRelationship', 'analyteType', 'primaryBiosample', 'tissueAffectedStatus', 'solveStatus',
}

NO_INTERNAL_CASE_REVIEW_INDIVIDUAL_FIELDS = deepcopy(INDIVIDUAL_FIELDS)
NO_INTERNAL_CASE_REVIEW_INDIVIDUAL_FIELDS.update(CASE_REVIEW_INDIVIDUAL_FIELDS)

INTERNAL_INDIVIDUAL_FIELDS = deepcopy(NO_INTERNAL_CASE_REVIEW_INDIVIDUAL_FIELDS)
INTERNAL_INDIVIDUAL_FIELDS.update(CORE_INTERNAL_INDIVIDUAL_FIELDS)

SAMPLE_FIELDS = {
    'projectGuid', 'familyGuid', 'individualGuid', 'sampleGuid', 'createdDate', 'sampleType', 'sampleId', 'isActive',
    'loadedDate', 'datasetType',
}

IGV_SAMPLE_FIELDS = {
    'projectGuid', 'familyGuid', 'individualGuid', 'sampleGuid', 'filePath', 'indexFilePath', 'sampleId', 'sampleType',
}

SAVED_VARIANT_FIELDS = {'variantGuid', 'variantId', 'familyGuids', 'xpos', 'ref', 'alt', 'selectedMainTranscriptId', 'acmgClassification'}
SAVED_VARIANT_DETAIL_FIELDS = {
    'chrom', 'pos', 'genomeVersion', 'liftedOverGenomeVersion', 'liftedOverChrom', 'liftedOverPos', 'tagGuids',
    'functionalDataGuids', 'noteGuids', 'originalAltAlleles', 'genotypes', 'hgmd', 'CAID',
    'transcripts', 'populations', 'predictions', 'rsid', 'genotypeFilters', 'clinvar', 'acmgClassification'
}
SAVED_VARIANT_DETAIL_FIELDS.update(SAVED_VARIANT_FIELDS)

TAG_FIELDS = {
    'tagGuid', 'name', 'category', 'color', 'searchHash', 'metadata', 'lastModifiedDate', 'createdBy', 'variantGuids',
}

VARIANT_NOTE_FIELDS = {'noteGuid', 'note', 'report', 'lastModifiedDate', 'createdBy', 'variantGuids'}

FUNCTIONAL_FIELDS = {
    'tagGuid', 'name', 'color', 'metadata', 'metadataTitle', 'lastModifiedDate', 'createdBy', 'variantGuids',
}

SAVED_SEARCH_FIELDS = {'savedSearchGuid', 'name', 'order', 'search', 'createdById'}

LOCUS_LIST_FIELDS = {
    'locusListGuid', 'description', 'lastModifiedDate', 'numEntries', 'isPublic', 'createdBy', 'createdDate', 'canEdit',
    'name',
}
PA_LOCUS_LIST_FIELDS = {'paLocusList'}
LOCUS_LIST_DETAIL_FIELDS = {'items', 'intervalGenomeVersion'}
LOCUS_LIST_DETAIL_FIELDS.update(LOCUS_LIST_FIELDS)

MATCHMAKER_SUBMISSION_FIELDS = {
    'submissionGuid', 'individualGuid', 'createdDate', 'lastModifiedDate', 'deletedDate',
}

TAG_TYPE_FIELDS = {
    'variantTagTypeGuid', 'name', 'category', 'description', 'color', 'order', 'metadataTitle',
}

GENE_FIELDS = {
    'chromGrch37', 'chromGrch38', 'codingRegionSizeGrch37', 'codingRegionSizeGrch38',  'endGrch37', 'endGrch38',
    'gencodeGeneType', 'geneId', 'geneSymbol', 'startGrch37', 'startGrch38',
}
GENE_VARIANT_DISPLAY_FIELDS = {
    'constraints', 'omimPhenotypes', 'mimNumber', 'cnSensitivity', 'genCc', 'clinGen', 'sHet',
}
GENE_VARIANT_DISPLAY_FIELDS.update(GENE_FIELDS)
GENE_VARIANT_FIELDS = {
    'diseaseDesc', 'functionDesc', 'geneNames', 'primateAi',
}
GENE_VARIANT_FIELDS.update(GENE_VARIANT_DISPLAY_FIELDS)

GENE_DETAIL_FIELDS = {'notes', 'mgiMarkerId'}
GENE_DETAIL_FIELDS.update(GENE_VARIANT_FIELDS)

VARIANTS = [
    {
        'alt': 'G',
        'ref': 'GAGA',
        'chrom': '21',
        'pos': 3343400,
        'xpos': 21003343400,
        'genomeVersion': '38',
        'liftedOverChrom': '21',
        'liftedOverPos': 3343353,
        'liftedOverGenomeVersion': '37',
        'variantId': '21-3343400-GAGA-G',
        'mainTranscriptId': 'ENST00000623083',
        'transcripts': {
            'ENSG00000227232': [
                {
                    'aminoAcids': 'G/S',
                    'geneSymbol': 'WASH7P',
                    'biotype': 'protein_coding',
                    'category': 'missense',
                    'cdnaEnd': 1075,
                    'cdnaStart': 1075,
                    'codons': 'Ggt/Agt',
                    'consequenceTerms': ['missense_variant'],
                    'hgvs': 'ENSP00000485442.1:p.Gly359Ser',
                    'hgvsc': 'ENST00000623083.3:c.1075G>A',
                    'hgvsp': 'ENSP00000485442.1:p.Gly359Ser',
                    'majorConsequence': 'missense_variant',
                    'majorConsequenceRank': 11,
                    'proteinId': 'ENSP00000485442',
                    'transcriptId': 'ENST00000623083',
                    'transcriptRank': 0
                }
            ],
            'ENSG00000268903': [
                {
                    'aminoAcids': 'G/S',
                    'biotype': 'protein_coding',
                    'category': 'missense',
                    'cdnaEnd': 1338,
                    'cdnaStart': 1338,
                    'codons': 'Ggt/Agt',
                    'consequenceTerms': ['missense_variant'],
                    'geneId': 'ENSG00000268903',
                    'hgvs': 'ENSP00000485351.1:p.Gly368Ser',
                    'hgvsc': 'ENST00000624735.1:c.1102G>A',
                    'hgvsp': 'ENSP00000485351.1:p.Gly368Ser',
                    'majorConsequence': 'missense_variant',
                    'majorConsequenceRank': 11,
                    'proteinId': 'ENSP00000485351',
                    'transcriptId': 'ENST00000624735',
                    'transcriptRank': 1
                }
            ]
        },
        'familyGuids': ['F000001_1', 'F000002_2'],
        'populations': {
            'callset': {'af': 0.13, 'ac': 4192, 'an': '32588'},
            'gnomad_genomes': {'af': 0.007},
        },
        'genotypeFilters': 'VQSRTrancheSNP99.95to100.00',
        'genotypes': {
            'NA19675': {
                'sampleId': 'NA19675',
                'ab': 0.702127659574,
                'gq': 46.0,
                'numAlt': 1,
                'dp': '50',
                'ad': '14,33'
            },
            'NA19679': {
                'sampleId': 'NA19679',
                'ab': 0.0,
                'gq': 99.0,
                'numAlt': 0,
                'dp': '45',
                'ad': '45,0'
            }
        }
    },
    {
        'alt': 'A',
        'ref': 'AAAG',
        'chrom': '3',
        'pos': 835,
        'xpos': 3000000835,
        'genomeVersion': '37',
        'liftedOverGenomeVersion': '',
        'variantId': '3-835-AAAG-A',
        'transcripts': {},
        'familyGuids': ['F000001_1'],
        'genotypes': {
            'NA19679': {
                'filters': ['artifact_prone_site'],
                'sampleId': 'NA19679',
                'ab': 0.0,
                'gq': 99.0,
                'numAlt': 0,
                'dp': '45',
                'ad': '45,0'
            }
        }
    },
    {
        'alt': 'T',
        'ref': 'TC',
        'chrom': '12',
        'pos': 48367227,
        'xpos': 1248367227,
        'genomeVersion': '37',
        'liftedOverGenomeVersion': '',
        'variantId': '1-248367227-TC-T',
        'transcripts': {'ENSG00000233653': {}},
        'familyGuids': ['F000002_2'],
        'genotypeFilters': '',
        'genotypes': {}
    }
]

SINGLE_VARIANT = {
    'alt': 'A',
    'ref': 'G',
    'chrom': '1',
    'pos': 46394160,
    'xpos': 1046394160,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'variantId': '1-46394160-G-A',
    'transcripts': {'ENSG00000233653': {}},
    'familyGuids': ['F000002_2'],
    'genotypes': {}
}

TRANSCRIPT_1 = {
  'aminoAcids': 'LL/L',
  'biotype': 'protein_coding',
  'lof': None,
  'lofFlags': None,
  'majorConsequenceRank': 10,
  'codons': 'ctTCTc/ctc',
  'geneSymbol': 'MFSD9',
  'domains': [
    'Transmembrane_helices:TMhelix',
    'PROSITE_profiles:PS50850',
  ],
  'canonical': 1,
  'transcriptRank': 0,
  'cdnaEnd': 421,
  'lofFilter': None,
  'hgvs': 'ENSP00000258436.5:p.Leu126del',
  'hgvsc': 'ENST00000258436.5:c.375_377delTCT',
  'cdnaStart': 419,
  'transcriptId': 'ENST00000258436',
  'proteinId': 'ENSP00000258436',
  'category': 'missense',
  'geneId': 'ENSG00000135953',
  'hgvsp': 'ENSP00000258436.5:p.Leu126del',
  'majorConsequence': 'inframe_deletion',
  'consequenceTerms': [
    'inframe_deletion'
  ]
}
TRANSCRIPT_2 = {
  'aminoAcids': 'P/X',
  'biotype': 'protein_coding',
  'lof': None,
  'lofFlags': None,
  'majorConsequenceRank': 4,
  'codons': 'Ccc/cc',
  'geneSymbol': 'OR2M3',
  'domains': [
    'Transmembrane_helices:TMhelix',
    'Prints_domain:PR00237',
  ],
  'canonical': 1,
  'transcriptRank': 0,
  'cdnaEnd': 897,
  'lofFilter': None,
  'hgvs': 'ENSP00000389625.1:p.Leu288SerfsTer10',
  'hgvsc': 'ENST00000456743.1:c.862delC',
  'cdnaStart': 897,
  'transcriptId': 'ENST00000456743',
  'proteinId': 'ENSP00000389625',
  'category': 'lof',
  'geneId': 'ENSG00000228198',
  'hgvsp': 'ENSP00000389625.1:p.Leu288SerfsTer10',
  'majorConsequence': 'frameshift_variant',
  'consequenceTerms': [
    'frameshift_variant'
  ]
}
TRANSCRIPT_3 = {
  'aminoAcids': 'LL/L',
  'biotype': 'nonsense_mediated_decay',
  'lof': None,
  'lofFlags': None,
  'majorConsequenceRank': 10,
  'codons': 'ctTCTc/ctc',
  'geneSymbol': 'MFSD9',
  'domains': [
    'Transmembrane_helices:TMhelix',
    'Gene3D:1',
  ],
  'canonical': None,
  'transcriptRank': 1,
  'cdnaEnd': 143,
  'lofFilter': None,
  'hgvs': 'ENSP00000413641.1:p.Leu48del',
  'hgvsc': 'ENST00000428085.1:c.141_143delTCT',
  'cdnaStart': 141,
  'transcriptId': 'ENST00000428085',
  'proteinId': 'ENSP00000413641',
  'category': 'missense',
  'geneId': 'ENSG00000135953',
  'hgvsp': 'ENSP00000413641.1:p.Leu48del',
  'majorConsequence': 'frameshift_variant',
  'consequenceTerms': [
    'frameshift_variant',
    'inframe_deletion',
    'NMD_transcript_variant'
  ]
}

PARSED_VARIANTS = [
    {
        'alt': 'T',
        'chrom': '1',
        'bothsidesSupport': None,
        'clinvar': {'clinicalSignificance': 'Pathogenic/Likely_pathogenic', 'alleleId': None, 'variationId': None, 'goldStars': None, 'version': '2023-03-05'},
        'commonLowHeteroplasmy': None,
        'highConstraintRegion': None,
        'mitomapPathogenic': None,
        'familyGuids': ['F000003_3'],
        'cpxIntervals': None,
        'algorithms': None,
        'genotypes': {
            'I000007_na20870': {
                'ab': 1, 'ad': None, 'gq': 99, 'sampleId': 'NA20870', 'numAlt': 2, 'dp': 74, 'pl': None,
                'sampleType': 'WES',
            }
        },
        'genomeVersion': '37',
        'genotypeFilters': '',
        'hgmd': {'accession': None, 'class': 'DM'},
        'mainTranscriptId': TRANSCRIPT_3['transcriptId'],
        'selectedMainTranscriptId': None,
        'originalAltAlleles': ['T'],
        'populations': {
            'callset': {'an': 32, 'ac': 2, 'hom': 3, 'af': 0.063, 'hemi': None, 'filter_af': None, 'het': None,
                        'id': None, 'max_hl': None},
            'gnomad_genomes': {'an': 30946, 'ac': 4, 'hom': 0, 'af': 0.00012925741614425127, 'hemi': 0,
                               'filter_af': 0.0004590314436538903, 'het': 0, 'id': None, 'max_hl': None},
            'exac': {'an': 121308, 'ac': 8, 'hom': 0, 'af': 0.00006589, 'hemi': 0, 'filter_af': 0.0006726888333653661,
                     'het': 0, 'id': None, 'max_hl': None},
            'gnomad_exomes': {'an': 245930, 'ac': 16, 'hom': 0, 'af': 0.00006505916317651364, 'hemi': 0,
                              'filter_af': 0.0009151523074911753, 'het': 0, 'id': None, 'max_hl': None},
            'topmed': {'an': 125568, 'ac': 21, 'hom': 0, 'af': 0.00016724, 'hemi': 0, 'filter_af': None, 'het': None,
                       'id': None, 'max_hl': None},
            'sv_callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None,
                           'het': None, 'id': None, 'max_hl': None},
            'gnomad_svs': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'hom': None,
                           'het': None, 'id': None, 'max_hl': None},
            'gnomad_mito': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                            'hom': None, 'id': None, 'max_hl': None},
            'helix': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None, 'hom': None,
                      'id': None, 'max_hl': None},
            'callset_heteroplasmy': {'ac': None, 'af': None, 'an': 32, 'filter_af': None, 'hemi': None, 'het': None,
                                     'hom': None, 'id': None, 'max_hl': None},
            'gnomad_mito_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None,
                                         'het': None, 'hom': None, 'id': None, 'max_hl': None},
            'helix_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                                   'hom': None, 'id': None, 'max_hl': None},
        },
        'pos': 248367227,
        'predictions': {'splice_ai': 0.75, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': 'D',
                        'vest': '0.335', 'mut_pred': None,
                        'hmtvar': None, 'apogee': None, 'haplogroup_defining': None, 'mitotip': None,
                        'polyphen': None, 'dann': None, 'sift': None, 'cadd': '25.9', 'primate_ai': None,
                        'mpc': None, 'strvctvre': None, 'splice_ai_consequence': None, 'gnomad_noncoding': 1.01272,},
        'ref': 'TC',
        'rsid': None,
        'screenRegionType': 'dELS',
        'transcripts': {
            'ENSG00000135953': [TRANSCRIPT_3],
            'ENSG00000228198': [TRANSCRIPT_2],
        },
        'variantId': '1-248367227-TC-T',
        'xpos': 1248367227,
        'end': None,
        'svType': None,
        'svTypeDetail': None,
        'numExon': None,
        'rg37LocusEnd': None,
        '_sort': [1248367227],
    },
    {
        'alt': 'G',
        'chrom': '2',
        'bothsidesSupport': None,
        'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None, 'version': '2023-03-05'},
        'commonLowHeteroplasmy': None,
        'highConstraintRegion': None,
        'mitomapPathogenic': None,
        'familyGuids': ['F000002_2', 'F000003_3'],
        'cpxIntervals': None,
        'algorithms': None,
        'genotypes': {
            'I000004_hg00731': {
                'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 2, 'dp': 67, 'pl': None,
                'sampleType': 'WES',
            },
            'I000005_hg00732': {
                'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00732', 'numAlt': 1, 'dp': 42, 'pl': None,
                'sampleType': 'WES',
            },
            'I000006_hg00733': {
                'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00733', 'numAlt': 0, 'dp': 42, 'pl': None,
                'sampleType': 'WES',
            },
            'I000007_na20870': {
                'ab': 0.70212764, 'ad': None, 'gq': 46, 'sampleId': 'NA20870', 'numAlt': 1, 'dp': 50, 'pl': None,
                'sampleType': 'WES',
            }
        },
        'genotypeFilters': '',
        'genomeVersion': '37',
        'hgmd': {'accession': None, 'class': None},
        'mainTranscriptId': TRANSCRIPT_1['transcriptId'],
        'selectedMainTranscriptId': TRANSCRIPT_2['transcriptId'],
        'originalAltAlleles': ['G'],
        'populations': {
            'callset': {'an': 32, 'ac': 1, 'hom': None, 'af': 0.031, 'hemi': None, 'filter_af': None, 'het': None,
                        'id': None, 'max_hl': None},
            'gnomad_genomes': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None, 'het': 0,
                               'id': None, 'max_hl': None},
            'exac': {'an': 121336, 'ac': 6, 'hom': 0, 'af': 0.00004942, 'hemi': 0, 'filter_af': 0.000242306760358614,
                     'het': 0, 'id': None, 'max_hl': None},
            'gnomad_exomes': {'an': 245714, 'ac': 6, 'hom': 0, 'af': 0.000024418633044922146, 'hemi': 0,
                              'filter_af': 0.00016269686320447742, 'het': 0, 'id': None, 'max_hl': None},
            'topmed': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None, 'het': None, 'id': None,
                       'max_hl': None},
            'sv_callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None,
                           'het': None, 'id': None, 'max_hl': None},
            'gnomad_svs': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'hom': None,
                           'het': None, 'id': None, 'max_hl': None},
            'gnomad_mito': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                            'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
            'helix': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                      'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
            'callset_heteroplasmy': {'ac': None, 'af': None, 'an': 32, 'filter_af': None, 'hemi': None, 'het': None,
                                     'hom': None, 'id': None, 'max_hl': None},
            'gnomad_mito_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None,
                                         'het': None, 'hom': None, 'id': None, 'max_hl': None},
            'helix_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                                   'hom': None, 'id': None, 'max_hl': None},
        },
        'pos': 103343353,
        'predictions': {
            'hmtvar': None, 'apogee': None, 'haplogroup_defining': None, 'mitotip': None, 'gnomad_noncoding': None,
            'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None, 'polyphen': None,
            'dann': None, 'sift': None, 'cadd': None, 'primate_ai': 1, 'vest': None, 'mut_pred': None,
            'mpc': None, 'strvctvre': None, 'splice_ai_consequence': None,
        },
        'ref': 'GAGA',
        'rsid': None,
        'screenRegionType': None,
        'transcripts': {
            'ENSG00000135953': [TRANSCRIPT_1],
            'ENSG00000228198': [TRANSCRIPT_2],
        },
        'variantId': '2-103343353-GAGA-G',
        'xpos': 2103343353,
        'end': None,
        'svType': None,
        'svTypeDetail': None,
        'numExon': None,
        'rg37LocusEnd': None,
        '_sort': [2103343353],
    },
]

PARSED_SV_VARIANT = {
    'alt': None,
    'chrom': '1',
    'bothsidesSupport': True,
    'familyGuids': ['F000002_2'],
    'cpxIntervals': None,
    'algorithms': None,
    'commonLowHeteroplasmy': None,
    'highConstraintRegion': None,
    'mitomapPathogenic': None,
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'numAlt': -1, 'geneIds': ['ENSG00000228198'],
            'cn': 1, 'end': None, 'start': None, 'numExon': None, 'defragged': False, 'qs': 33, 'gq': None,
            'prevCall': False, 'prevOverlap': False, 'newCall': True, 'prevNumAlt': None,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'numAlt': -1, 'sampleType': None,  'geneIds': None, 'gq': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None, 'isRef': True,
            'prevCall': None, 'prevOverlap': None, 'newCall': None, 'prevNumAlt': None,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'numAlt': -1,  'geneIds': None, 'gq': None,
            'cn': 2, 'end': 49045890, 'start': 49045987, 'numExon': 1, 'defragged': False, 'qs': 80,
            'prevCall': False, 'prevOverlap': True, 'newCall': False, 'prevNumAlt': None,
        },
    },
    'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None, 'version': None},
    'hgmd': {'accession': None, 'class': None},
    'genomeVersion': '37',
    'genotypeFilters': '',
    'mainTranscriptId': None,
    'selectedMainTranscriptId': None,
    'originalAltAlleles': [],
    'populations': {
        'callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None,
                    'id': None, 'max_hl': None},
        'gnomad_genomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None,
                           'het': None, 'id': None, 'max_hl': None},
        'exac': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None,
                 'id': None, 'max_hl': None},
        'gnomad_exomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None,
                          'id': None, 'max_hl': None},
        'topmed': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None,
                   'id': None, 'max_hl': None},
        'sv_callset': {'an': 10088, 'ac': 7, 'hom': None, 'af': 0.000693825, 'hemi': None, 'filter_af': None,
                       'het': None, 'id': None, 'max_hl': None},
        'gnomad_svs': {'ac': 0, 'af': 0.0, 'an': 0, 'filter_af': None, 'hemi': 0, 'hom': 0, 'het': 0, 'id': None,
                       'max_hl': None},
        'gnomad_mito': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                        'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
        'helix': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                  'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
        'callset_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                                 'hom': None, 'id': None, 'max_hl': None},
        'gnomad_mito_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                                 'hom': None, 'id': None, 'max_hl': None},
        'helix_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                                     'hom': None, 'id': None, 'max_hl': None},
    },
    'pos': 49045487,
    'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None,
                    'hmtvar': None, 'apogee': None, 'haplogroup_defining': None, 'mitotip': None, 'gnomad_noncoding': None,
                    'polyphen': None, 'dann': None, 'sift': None, 'cadd': None, 'primate_ai': None,
                    'vest': None, 'mut_pred': None, 'mpc': None, 'strvctvre': 0.374, 'splice_ai_consequence': None},
    'ref': None,
    'rsid': None,
    'screenRegionType': None,
    'transcripts': {
        'ENSG00000228198': [
            {
              'geneId': 'ENSG00000228198'
            },
        ],
        'ENSG00000135953': [
            {
              'geneId': 'ENSG00000135953'
            },
        ],
    },
    'variantId': 'prefix_19107_DEL',
    'xpos': 1049045487,
    'end': 49045899,
    'svType': 'INS',
    'svTypeDetail': None,
    'svSourceDetail': {'chrom': '9'},
    'numExon': 2,
    'rg37LocusEnd': None,
    '_sort': [1049045387],
}

PARSED_SV_WGS_VARIANT = {
    'alt': None,
    'chrom': '2',
    'bothsidesSupport': None,
    'familyGuids': ['F000014_14'],
    'cpxIntervals': [{'chrom': '2', 'end': 3000, 'start': 1000, 'type': 'DUP'},
                     {'chrom': '20', 'end': 13000, 'start': 11000, 'type': 'INV'}],
    'algorithms': 'wham, manta',
    'commonLowHeteroplasmy': None,
    'highConstraintRegion': None,
    'mitomapPathogenic': None,
    'genotypes': {
        'I000018_na21234': {
            'gq': 33, 'sampleId': 'NA21234', 'numAlt': 1, 'geneIds': None,
            'cn': -1, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None, 'sampleType': 'WGS',
            'prevCall': None, 'prevOverlap': None, 'newCall': None, 'prevNumAlt': 2,
        },
    },
    'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None, 'version': None},
    'hgmd': {'accession': None, 'class': None},
    'genomeVersion': '38',
    'genotypeFilters': '',
    'liftedOverChrom': '2',
    'liftedOverGenomeVersion': '37',
    'liftedOverPos': 49272526,
    'mainTranscriptId': None,
    'selectedMainTranscriptId': None,
    'originalAltAlleles': [],
    'populations': {
        'callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None,
                    'id': None, 'max_hl': None},
        'gnomad_genomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None,
                           'het': None, 'id': None, 'max_hl': None},
        'exac': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None,
                 'id': None, 'max_hl': None},
        'gnomad_exomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None,
                          'id': None, 'max_hl': None},
        'topmed': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None,
                   'id': None, 'max_hl': None},
        'sv_callset': {'an': 10088, 'ac': 7, 'hom': None, 'af': 0.000693825, 'hemi': None, 'filter_af': None,
                       'het': None, 'id': None, 'max_hl': None},
        'gnomad_svs': {'ac': 22, 'af': 0.00679, 'an': 3240, 'filter_af': None, 'hemi': 0, 'hom': 0, 'het': 0,
                       'id': 'gnomAD-SV_v2.1_BND_1_1', 'max_hl': None},
        'gnomad_mito': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                        'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
        'helix': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                  'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
        'callset_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                                 'hom': None, 'id': None, 'max_hl': None},
        'gnomad_mito_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                                     'hom': None, 'id': None, 'max_hl': None},
        'helix_heteroplasmy': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                               'hom': None, 'id': None, 'max_hl': None},
    },
    'pos': 49045387,
    'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None,
                    'vest': None, 'mut_pred': None,
                    'hmtvar': None, 'apogee': None, 'haplogroup_defining': None, 'mitotip': None,
                    'polyphen': None, 'dann': None, 'sift': None, 'cadd': None, 'primate_ai': None,
                    'mpc': None, 'strvctvre': None, 'gnomad_noncoding': None, 'splice_ai_consequence': None},
    'ref': None,
    'rsid': None,
    'screenRegionType': None,
    'transcripts': {
        'ENSG00000228198': [
            {
                'geneSymbol': 'OR4F5',
                'majorConsequence': 'DUP_PARTIAL',
                'geneId': 'ENSG00000228198'
            },
        ],
        'ENSG00000228199': [
            {
                'geneId': 'ENSG00000228199',
                'geneSymbol': 'FBXO28',
                'majorConsequence': 'MSV_EXON_OVERLAP'
            }
        ],
        'ENSG00000228201': [
            {
                'geneId': 'ENSG00000228201',
                'geneSymbol': 'FAM131C',
                'majorConsequence': 'INTRAGENIC_EXON_DUP'
            }
        ]
    },
    'variantId': 'prefix_19107_CPX',
    'xpos': 2049045387,
    'end': 12345678,
    'endChrom': '20',
    'svType': 'CPX',
    'svTypeDetail': 'dupINV',
    'numExon': None,
    'rg37LocusEnd': {'contig': '20', 'position': 12326326},
    '_sort': [2049045387],
}

PARSED_MITO_VARIANT = {
    '_sort': [25000010195],
    'algorithms': None,
    'alt': 'A',
    'bothsidesSupport': None,
    'chrom': 'M',
    'clinvar': {'alleleId': None, 'clinicalSignificance': 'Likely_pathogenic', 'goldStars': None, 'variationId': None, 'version': None},
    'commonLowHeteroplasmy': False,
    'cpxIntervals': None,
    'end': 10195,
    'familyGuids': ['F000002_2'],
    'genomeVersion': '37',
    'genotypeFilters': '',
    'genotypes':
        {'I000004_hg00731':
             {'contamination': 0.0, 'dp': 5139.0, 'gq': 60.0, 'hl': 1.0, 'mitoCn': 319.03225806451616, 'numAlt': 2,
              'sampleId': 'HG00731', 'sampleType': 'WES'}},
    'hgmd': {'accession': None, 'class': None},
    'highConstraintRegion': True,
    'mainTranscriptId': 'ENST00000361227',
    'mitomapPathogenic': True,
    'numExon': None,
    'originalAltAlleles': [],
    'populations':
        {'callset': {'ac': 0, 'af': 0.0, 'an': 2520, 'filter_af': None, 'hemi': None,
              'het': None, 'hom': None, 'id': None, 'max_hl': None},
         'exac': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None,
              'het': None, 'hom': None, 'id': None, 'max_hl': None},
         'gnomad_exomes': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                           'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
         'gnomad_genomes': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                            'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
         'gnomad_mito': {'ac': 1368, 'af': 0.024246292, 'an': 56421, 'filter_af': None, 'hemi': None,
                         'het': None, 'hom': None, 'id': None,'max_hl': None},
         'gnomad_svs': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                        'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
         'helix': {'ac': 1312, 'af': 0.0033268193, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                   'hom': None, 'id': None, 'max_hl': None},
         'sv_callset': {'ac': None, 'af': None, 'an': None, 'filter_af': None,
                        'hemi': None, 'het': None, 'hom': None, 'id': None, 'max_hl': None},
         'topmed': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None,
                    'het': None, 'hom': None, 'id': None, 'max_hl': None},
         'callset_heteroplasmy': {'ac': 1, 'af': 0.0003968253968253968, 'an': 2520, 'filter_af': None, 'hemi': None, 'het': None,
                                  'hom': None, 'id': None, 'max_hl': None},
         'gnomad_mito_heteroplasmy': {'ac': 3, 'af': 5.317169e-05, 'an': 56421, 'filter_af': None, 'hemi': None, 'het': None,
                                      'hom': None, 'id': None, 'max_hl': 1.0},
         'helix_heteroplasmy': {'ac': 5, 'af': 4.081987e-05, 'an': None, 'filter_af': None, 'hemi': None, 'het': None,
                                'hom': None, 'id': None, 'max_hl': 0.90441},
        },
    'pos': 10195,
    'predictions': {'hmtvar': 0.71, 'apogee': 0.42, 'cadd': None, 'dann': None, 'eigen': None, 'fathmm': 'T',
                    'haplogroup_defining': None, 'mitotip': None, 'mpc': None, 'mut_taster': 'N', 'polyphen': None,
                    'primate_ai': None, 'revel': None, 'sift': 'D', 'splice_ai': None, 'splice_ai_consequence': None,
                    'vest': None, 'mut_pred': None, 'strvctvre': None, 'gnomad_noncoding': None,},
    'ref': 'C',
    'rg37LocusEnd': None,
    'rsid': None,
    'screenRegionType': None,
    'selectedMainTranscriptId': None,
    'svType': None,
    'svTypeDetail': None,
    'transcripts': {'ENSG00000198840': [
        {'aminoAcids': 'P/H', 'biotype': 'protein_coding', 'canonical': 1, 'category': 'missense', 'cdnaEnd': 137,
         'cdnaStart': 137, 'codons': 'cCc/cAc', 'consequenceTerms': [
            'missense_variant'],
         'domains': ['Gene3D:1', 'ENSP_mappings:5xtc', 'ENSP_mappings:5xtd', 'Pfam:PF00507', 'PANTHER:PTHR11058',
                     'PANTHER:PTHR11058'], 'geneId': 'ENSG00000198840', 'geneSymbol': 'MT-ND3', 'hgvs': 'p.Pro46His',
         'hgvsc': 'ENST00000361227.2:c.137C>A', 'hgvsp': 'ENSP00000355206.2:p.Pro46His',
         'majorConsequence': 'missense_variant', 'majorConsequenceRank': 11,
         'polyphenPrediction': 'probably_damaging', 'proteinId': 'ENSP00000355206', 'proteinStart': 46,
         'siftPrediction': 'deleterious_low_confidence', 'transcriptId': 'ENST00000361227', 'transcriptRank': 0}]},
    'variantId': 'M-10195-C-A',
    'xpos': 25000010195
}

PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT = deepcopy(PARSED_VARIANTS)
PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT[1].update({
    'familyGuids': ['F000003_3'],
    'mainTranscriptId': TRANSCRIPT_2['transcriptId'],
    'selectedMainTranscriptId': None,
})
PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT[1]['transcripts']['ENSG00000135953'][0]['majorConsequence'] = 'frameshift_variant'
for variant in PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT:
    variant['_sort'][0] += 100
    variant['familyGuids'].append('F000011_11')
    variant['genotypes'].update({
        'I000015_na20885': {
            'ab': 0.631, 'ad': None, 'gq': 99, 'sampleId': 'NA20885', 'numAlt': 1, 'dp': 50, 'pl': None,
            'sampleType': 'WES',
        },
    })

GOOGLE_API_TOKEN_URL = 'https://oauth2.googleapis.com/token'  # nosec
GOOGLE_ACCESS_TOKEN_URL = 'https://accounts.google.com/o/oauth2/token'  # nosec

GOOGLE_TOKEN_RESULT = '{"access_token":"ya29.c.EXAMPLE","expires_in":3599,"token_type":"Bearer"}'  # nosec
