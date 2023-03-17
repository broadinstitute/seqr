import json
import mock
from copy import deepcopy
from datetime import datetime
from django.contrib.auth.models import Group
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.project_api import create_project_handler, delete_project_handler, update_project_handler, \
    project_page_data, project_families, project_overview, project_mme_submisssions, project_individuals, \
    project_analysis_groups, update_project_workspace, project_family_notes, project_collaborators, project_locus_lists
from seqr.views.utils.terra_api_utils import TerraAPIException, TerraRefreshTokenFailedException
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, \
    PROJECT_FIELDS, LOCUS_LIST_FIELDS, PA_LOCUS_LIST_FIELDS, NO_INTERNAL_CASE_REVIEW_INDIVIDUAL_FIELDS, \
    SAMPLE_FIELDS, FAMILY_FIELDS, INTERNAL_FAMILY_FIELDS, INTERNAL_INDIVIDUAL_FIELDS, INDIVIDUAL_FIELDS, TAG_TYPE_FIELDS, \
    CASE_REVIEW_FAMILY_FIELDS, FAMILY_NOTE_FIELDS, MATCHMAKER_SUBMISSION_FIELDS, ANALYSIS_GROUP_FIELDS, \
    TEST_WORKSPACE_NAMESPACE, TEST_NO_PROJECT_WORKSPACE_NAME2

PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'
DEMO_PROJECT_GUID = 'R0003_test'

PROJECT_PAGE_RESPONSE_KEYS = {'projectsByGuid'}

BASE_CREATE_PROJECT_JSON = {
    'name': 'new_project', 'description': 'new project description', 'genomeVersion': '38', 'isDemo': True,
    'disableMme': True, 'consentCode': 'H',
}
WORKSPACE_JSON = {'workspaceName': TEST_NO_PROJECT_WORKSPACE_NAME2, 'workspaceNamespace': TEST_WORKSPACE_NAMESPACE}
WORKSPACE_CREATE_PROJECT_JSON = deepcopy(WORKSPACE_JSON)
WORKSPACE_CREATE_PROJECT_JSON.update(BASE_CREATE_PROJECT_JSON)

MOCK_GROUP_UUID = '123abd'

class ProjectAPITest(object):
    CREATE_PROJECT_JSON = WORKSPACE_CREATE_PROJECT_JSON
    REQUIRED_FIELDS = ['name', 'genomeVersion', 'workspaceNamespace', 'workspaceName']

    @mock.patch('seqr.models.uuid.uuid4', lambda: MOCK_GROUP_UUID)
    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    def test_create_and_delete_project(self):
        create_project_url = reverse(create_project_handler)
        self.check_pm_login(create_project_url)

        # check validation of bad requests
        response = self.client.post(create_project_url, content_type='application/json',
                                    data=json.dumps({'bad_json': None}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], f'Field(s) "{", ".join(self.REQUIRED_FIELDS)}" are required')

        if 'workspaceName' in self.CREATE_PROJECT_JSON:
            project_json = {'workspaceName': 'foo', 'workspaceNamespace': 'bar'}
            project_json.update(BASE_CREATE_PROJECT_JSON)
            response = self.client.post(create_project_url, content_type='application/json', data=json.dumps(project_json))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error'], 'Invalid Workspace')

        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps(self.CREATE_PROJECT_JSON))
        self.assertEqual(response.status_code, 200)

        # check that project was created
        new_project = Project.objects.get(name='new_project')
        self.assertEqual(new_project.description, 'new project description')
        self.assertEqual(new_project.genome_version, '38')
        self.assertEqual(new_project.consent_code, 'H')
        self.assertTrue(new_project.is_demo)
        self.assertFalse(new_project.is_mme_enabled)
        self.assertEqual(new_project.created_by, self.pm_user)
        self.assertEqual(new_project.projectcategory_set.count(), 0)
        expected_workspace_name = self.CREATE_PROJECT_JSON.get('workspaceName')
        self.assertEqual(new_project.workspace_name, expected_workspace_name)
        self._check_created_project_groups(new_project)

        project_guid = new_project.guid
        self.assertSetEqual(set(response.json()['projectsByGuid'].keys()), {project_guid})
        self.assertTrue(response.json()['projectsByGuid'][project_guid]['userIsCreator'])

        # delete the project
        delete_project_url = reverse(delete_project_handler, args=[project_guid])
        response = self.client.post(delete_project_url, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # check that project was deleted
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 0)
        self.assertEqual(
            Group.objects.filter(name__in=['new_project_can_edit_123abd', 'new_project_can_view_123abd']).count(), 0,
        )

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    def test_update_project(self):
        update_project_url = reverse(update_project_handler, args=[PROJECT_GUID])
        self.check_manager_login(update_project_url)

        project = Project.objects.get(guid=PROJECT_GUID)
        expected_workspace_name = project.workspace_name
        self.assertEqual(project.genome_version, '37')
        self.assertEqual(project.consent_code, 'H')

        response = self.client.post(update_project_url, content_type='application/json', data=json.dumps(
            {'description': 'updated project description', 'genomeVersion': '38', 'workspaceName': 'test update name'}
        ))
        self.assertEqual(response.status_code, 200)
        updated_json = response.json()['projectsByGuid'][PROJECT_GUID]
        self.assertEqual(updated_json['description'], 'updated project description')
        # genome version and workspace should not update
        self.assertEqual(updated_json['genomeVersion'], '37')
        self.assertEqual(updated_json['workspaceName'], expected_workspace_name)
        updated_project = Project.objects.get(guid=PROJECT_GUID)
        self.assertEqual(updated_project.description, 'updated project description')
        self.assertEqual(updated_project.genome_version, '37')
        self.assertEqual(updated_project.workspace_name, expected_workspace_name)

        # test consent code
        response = self.client.post(update_project_url, content_type='application/json', data=json.dumps(
            {'consentCode': 'G'}
        ))
        self.assertEqual(response.status_code, 403)
        self.login_pm_user()
        response = self.client.post(update_project_url, content_type='application/json', data=json.dumps(
            {'consentCode': 'G'}
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['projectsByGuid'][PROJECT_GUID]['consentCode'], 'G')
        self.assertEqual(Project.objects.get(guid=PROJECT_GUID).consent_code, 'G')

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', None)
    def test_create_project_no_pm(self):
        create_project_url = reverse(create_project_handler)
        self.check_superuser_login(create_project_url)

        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps(
            {'name': 'new_project', 'description': 'new project description', 'genomeVersion': '38'}
        ))
        self.assertEqual(response.status_code, 200)

        # check that project was created
        new_project = Project.objects.get(name='new_project')
        self.assertEqual(new_project.description, 'new project description')
        self.assertEqual(new_project.genome_version, '38')
        self.assertFalse(new_project.is_demo)
        self.assertTrue(new_project.is_mme_enabled)
        self.assertIsNone(new_project.consent_code)
        self.assertEqual(new_project.created_by, self.super_user)
        self.assertListEqual([], list(new_project.projectcategory_set.all()))

        self.assertSetEqual(set(response.json()['projectsByGuid'].keys()), {new_project.guid})

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    def test_update_project_workspace(self):
        url = reverse(update_project_workspace, args=[PROJECT_GUID])
        self.check_pm_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid Workspace')

        response = self.client.post(url, content_type='application/json', data=json.dumps({'workspaceName': 'foo', 'workspaceNamespace': 'bar'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid Workspace')

        update_json = {'genomeVersion': '38', 'description': 'updated project description'}
        update_json.update(WORKSPACE_JSON)
        response = self.client.post(url, content_type='application/json', data=json.dumps(update_json))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), PROJECT_FIELDS)

        self.assertEqual(response_json['workspaceName'], TEST_NO_PROJECT_WORKSPACE_NAME2)
        self.assertEqual(response_json['workspaceNamespace'], TEST_WORKSPACE_NAMESPACE)
        self.assertEqual(response_json['genomeVersion'], '37')
        self.assertNotEqual(response_json['description'], 'updated project description')

        project = Project.objects.get(guid=PROJECT_GUID)
        self.assertEqual(project.workspace_name, TEST_NO_PROJECT_WORKSPACE_NAME2)
        self.assertEqual(project.workspace_namespace, TEST_WORKSPACE_NAMESPACE)

    def test_project_page_data(self):
        url = reverse(project_page_data, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), PROJECT_PAGE_RESPONSE_KEYS)
        project_fields = set()
        project_fields.update(PROJECT_FIELDS)
        project_fields.remove('projectCategoryGuids')
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), project_fields)
        self.assertEqual(
            response_json['projectsByGuid'][PROJECT_GUID]['lastAccessedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )

        # Test invalid project guid
        invalid_url = reverse(project_page_data, args=['FAKE_GUID'])
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'Project matching query does not exist.')

    def test_all_user_demo_project_page_data(self):
        Project.objects.update(all_user_demo=True)
        url = reverse(project_page_data, args=[DEMO_PROJECT_GUID])
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), PROJECT_PAGE_RESPONSE_KEYS)
        self.assertListEqual(list(response_json['projectsByGuid'].keys()), [DEMO_PROJECT_GUID])
        self.assertFalse(response_json['projectsByGuid'][DEMO_PROJECT_GUID]['canEdit'])

    def _check_empty_project(self, empty_url, response_keys):
        response = self.client.get(empty_url)
        if self.HAS_EMPTY_PROJECT:
            self.assertEqual(response.status_code, 200)
            response_json = response.json()
            self.assertSetEqual(set(response_json.keys()), response_keys)
            expected_response = {k: {EMPTY_PROJECT_GUID: mock.ANY} if k == 'projectsByGuid' else {} for k in response_keys}
            self.assertDictEqual(response_json, expected_response)
        else:
            self.assertEqual(response.status_code, 403)

    def test_project_overview(self):
        url = reverse(project_overview, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {
            'projectsByGuid', 'samplesByGuid', 'familyTagTypeCounts',
        }
        self.assertSetEqual(set(response_json.keys()), response_keys)

        project_fields = {
            'variantTagTypes', 'variantFunctionalTagTypes',
            'projectGuid', 'mmeDeletedSubmissionCount', 'mmeSubmissionCount',
        }
        project_response = response_json['projectsByGuid'][PROJECT_GUID]
        self.assertSetEqual(set(project_response.keys()), project_fields)
        tag_type_fields = {'numTags'}
        tag_type_fields.update(TAG_TYPE_FIELDS)
        self.assertSetEqual(set(project_response['variantTagTypes'][0].keys()), tag_type_fields)
        note_tag_type = project_response['variantTagTypes'][-1]
        self.assertDictEqual(note_tag_type, {
            'variantTagTypeGuid': 'notes',
            'name': 'Has Notes',
            'category': 'Notes',
            'description': '',
            'color': 'grey',
            'order': 100,
            'numTags': 1,
        })
        mme_tag_type = project_response['variantTagTypes'][-2]
        self.assertDictEqual(mme_tag_type, {
            'variantTagTypeGuid': 'mmeSubmissionVariants',
            'name': 'MME Submission',
            'category': 'Matchmaker',
            'description': '',
            'color': '#6435c9',
            'order': 99,
            'numTags': 1,
        })
        self.assertEqual(project_response['mmeSubmissionCount'], 1)
        self.assertEqual(project_response['mmeDeletedSubmissionCount'], 0)

        self.assertSetEqual(set(next(iter(response_json['samplesByGuid'].values())).keys()), SAMPLE_FIELDS)
        self.assertDictEqual(response_json['familyTagTypeCounts'],  {
            'F000001_1': {'Review': 1, 'Tier 1 - Novel gene and phenotype': 1, 'MME Submission': 1},
            'F000002_2': {'Excluded': 1, 'Known gene for phenotype': 1},
        })

        # Test compound het counts
        comp_het_url = reverse(project_overview, args=[DEMO_PROJECT_GUID])
        response = self.client.get(comp_het_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json()['familyTagTypeCounts'],
            {'F000012_12': {'Tier 1 - Novel gene and phenotype': 1, 'MME Submission': 2}},
        )

        # Test empty project
        empty_url = reverse(project_overview, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys)

    def test_project_collaborators(self):
        url = reverse(project_collaborators, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertDictEqual(response.json(), {'projectsByGuid': {PROJECT_GUID: {
            'collaborators': self.PROJECT_COLLABORATORS,
            'collaboratorGroups': self.PROJECT_COLLABORATOR_GROUPS,
        }}})

        # Test empty project
        empty_url = reverse(project_collaborators, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, {'projectsByGuid'})

        if hasattr(self, 'mock_get_ws_acl'):
            self.mock_get_ws_acl.side_effect = TerraAPIException('AnVIL Error', 400)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error'], 'AnVIL Error')

            self.mock_get_ws_acl.side_effect = TerraRefreshTokenFailedException('Refresh Error')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['error'], '/login')

    def test_project_families(self):
        url = reverse(project_families, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'familiesByGuid', 'genesById'}
        self.assertSetEqual(set(response_json.keys()), response_keys)

        family_1 = response_json['familiesByGuid']['F000001_1']
        family_3 = response_json['familiesByGuid']['F000003_3']
        family_fields = {
            'individualGuids', 'discoveryTags', 'caseReviewStatuses', 'caseReviewStatusLastModified', 'hasRequiredMetadata',
            'parents',
        }
        family_fields.update(FAMILY_FIELDS)
        self.assertSetEqual(set(family_1.keys()), family_fields)

        self.assertEqual(len(family_1['individualGuids']), 3)
        self.assertEqual(len(family_3['individualGuids']), 1)
        self.assertListEqual(family_1['caseReviewStatuses'], ['A', 'I', 'U'])
        self.assertListEqual(family_3['caseReviewStatuses'], [])
        self.assertEqual(family_1['caseReviewStatusLastModified'], '2017-03-12T22:34:49.964Z')
        self.assertIsNone(family_3['caseReviewStatusLastModified'])
        self.assertTrue(family_1['hasRequiredMetadata'])
        self.assertFalse(family_3['hasRequiredMetadata'])
        self.assertListEqual(family_1['parents'], [{'maternalGuid': 'I000003_na19679', 'paternalGuid': 'I000002_na19678'}])
        self.assertListEqual(family_3['parents'], [])

        self.assertListEqual(family_3['discoveryTags'], [])
        self.assertSetEqual({tag['variantGuid'] for tag in family_1['discoveryTags']}, {'SV0000001_2103343353_r0390_100'})
        self.assertSetEqual(
            {tag['variantGuid'] for tag in response_json['familiesByGuid']['F000002_2']['discoveryTags']},
            {'SV0000002_1248367227_r0390_100'})
        no_discovery_families = set(response_json['familiesByGuid'].keys()) - {'F000001_1', 'F000002_2'}
        self.assertSetEqual({
            len(response_json['familiesByGuid'][family_guid]['discoveryTags']) for family_guid in no_discovery_families
        }, {0})

        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000135953'})

        # Test empty project
        empty_url = reverse(project_families, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys)

        # Test analyst users have internal fields returned
        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        family_fields.update(CASE_REVIEW_FAMILY_FIELDS)
        internal_fields = deepcopy(family_fields)
        internal_fields.update(INTERNAL_FAMILY_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['familiesByGuid'].values())).keys()), internal_fields)

        self.mock_analyst_group.__str__.return_value = ''
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(next(iter(response.json()['familiesByGuid'].values())).keys()), family_fields)

    def test_project_individuals(self):
        url = reverse(project_individuals, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'individualsByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)

        self.assertSetEqual(set(next(iter(response_json['individualsByGuid'].values())).keys()), INDIVIDUAL_FIELDS)
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000001_na19675']['features'][0].keys()),
            {'id', 'category', 'label'}
        )
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000001_na19675']['absentFeatures'][0].keys()),
            {'id', 'category', 'label'}
        )

        # Test empty project
        empty_url = reverse(project_individuals, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys)

        # Test analyst users have internal fields returned
        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(next(iter(response_json['individualsByGuid'].values())).keys()), INTERNAL_INDIVIDUAL_FIELDS)

        self.mock_analyst_group.__str__.return_value = ''
        self.mock_analyst_group.resolve_expression.return_value = ''
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(
            set(next(iter(response.json()['individualsByGuid'].values())).keys()),
            NO_INTERNAL_CASE_REVIEW_INDIVIDUAL_FIELDS,
        )

    def test_project_analysis_groups(self):
        url = reverse(project_analysis_groups, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'analysisGroupsByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertEqual(len(response_json['analysisGroupsByGuid']), 2)
        self.assertSetEqual(
            set(next(iter(response_json['analysisGroupsByGuid'].values())).keys()), ANALYSIS_GROUP_FIELDS
        )

    def test_project_locus_lists(self):
        url = reverse(project_locus_lists, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'projectsByGuid', 'locusListsByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertDictEqual(response_json['projectsByGuid'], {PROJECT_GUID: {
            'locusListGuids': ['LL00049_pid_genes_autosomal_do', 'LL00005_retina_proteome'],
        }})
        self.assertEqual(len(response_json['locusListsByGuid']), 2)
        self.assertSetEqual(set(response_json['locusListsByGuid']['LL00005_retina_proteome'].keys()), LOCUS_LIST_FIELDS)
        pa_fields = deepcopy(LOCUS_LIST_FIELDS)
        pa_fields.update(PA_LOCUS_LIST_FIELDS)
        self.assertSetEqual(set(response_json['locusListsByGuid']['LL00049_pid_genes_autosomal_do'].keys()), pa_fields)

    def test_project_family_notes(self):
        url = reverse(project_family_notes, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'familyNotesByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertEqual(len(response_json['familyNotesByGuid']), 3)
        self.assertSetEqual(
            set(next(iter(response_json['familyNotesByGuid'].values())).keys()), FAMILY_NOTE_FIELDS
        )

        # Test empty project
        empty_url = reverse(project_family_notes, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys)

    def test_project_mme_submisssions(self):
        url = reverse(project_mme_submisssions, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'mmeSubmissionsByGuid', 'familyNotesByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertSetEqual(set(response_json['mmeSubmissionsByGuid'].keys()), {'MS000001_na19675'})
        submission_fields = {'geneIds'}
        submission_fields.update(MATCHMAKER_SUBMISSION_FIELDS)
        self.assertSetEqual(set(response_json['mmeSubmissionsByGuid']['MS000001_na19675'].keys()), submission_fields)
        self.assertListEqual(response_json['mmeSubmissionsByGuid']['MS000001_na19675']['geneIds'], ['ENSG00000135953'])
        self.assertSetEqual(set(next(iter(response_json['familyNotesByGuid'].values())).keys()), FAMILY_NOTE_FIELDS)

        # Test empty project
        empty_url = reverse(project_mme_submisssions, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys)


BASE_COLLABORATORS = [
    {'displayName': 'Test Manager User', 'email': 'test_user_manager@test.com',  'username': 'test_user_manager',
     'hasEditPermissions': True, 'hasViewPermissions': True},
    {'displayName': 'Test Collaborator User', 'email': 'test_user_collaborator@test.com', 'username': 'test_user_collaborator',
     'hasEditPermissions': False, 'hasViewPermissions': True}]

ANVIL_COLLABORATORS = [
    {'displayName': '', 'email': 'analysts@firecloud.org', 'username': 'analysts@firecloud.org',
    'hasEditPermissions': True, 'hasViewPermissions': True, },
] + deepcopy(BASE_COLLABORATORS) + [{
    'displayName': '', 'email': 'test_user_pure_anvil@test.com', 'username': 'test_user_pure_anvil@test.com',
    'hasEditPermissions': False, 'hasViewPermissions': True, }]


# Tests for AnVIL access disabled
class LocalProjectAPITest(AuthenticationTestCase, ProjectAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']
    PROJECT_COLLABORATORS = BASE_COLLABORATORS
    CREATE_PROJECT_JSON = BASE_CREATE_PROJECT_JSON
    PROJECT_COLLABORATOR_GROUPS = [{'name': 'analysts', 'hasViewPermissions': True, 'hasEditPermissions': True}]
    REQUIRED_FIELDS = ['name', 'genomeVersion']
    HAS_EMPTY_PROJECT = True

    def _check_created_project_groups(self, project):
        self.assertEqual(project.can_edit_group.name, 'new_project_can_edit_123abd')
        self.assertEqual(project.can_view_group.name, 'new_project_can_view_123abd')
        self.assertSetEqual(set(project.can_edit_group.user_set.all()), {self.pm_user})
        self.assertSetEqual(set(project.can_view_group.user_set.all()), {self.pm_user})

    def test_update_project_workspace(self):
        url = reverse(update_project_workspace, args=[PROJECT_GUID])
        # For non-AnVIL seqr, updating workspace should always fail
        self.login_pm_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps(WORKSPACE_JSON))
        self.assertEqual(response.status_code, 403)


# Test for permissions from AnVIL only
class AnvilProjectAPITest(AnvilAuthenticationTestCase, ProjectAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    PROJECT_COLLABORATORS = ANVIL_COLLABORATORS
    PROJECT_COLLABORATOR_GROUPS = None
    HAS_EMPTY_PROJECT = False

    def test_create_and_delete_project(self):
        super(AnvilProjectAPITest, self).test_create_and_delete_project()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_group_members.assert_not_called()
        self.mock_get_groups.assert_has_calls([
            mock.call(self.collaborator_user), mock.call(self.manager_user), mock.call(self.analyst_user),
            mock.call(self.pm_user)])
        self.mock_get_ws_access_level.assert_has_calls([
            mock.call(self.pm_user, 'bar', 'foo'),
            mock.call(self.pm_user, 'my-seqr-billing', 'anvil-no-project-workspace2'),
        ])

    def _check_created_project_groups(self, project):
        self.assertIsNone(project.can_edit_group)
        self.assertIsNone(project.can_view_group)

    def test_create_project_no_pm(self):
        # Fallng back to superusers as PMs is only supported for local installs
        pass

    def test_update_project(self):
        super(AnvilProjectAPITest, self).test_update_project()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_group_members.assert_not_called()
        self.mock_get_groups.assert_has_calls([mock.call(self.manager_user), mock.call(self.pm_user)])
        self.mock_get_ws_access_level.assert_has_calls([
            mock.call(self.collaborator_user, 'my-seqr-billing', 'anvil-1kg project nåme with uniçøde'),
            mock.call(self.manager_user, 'my-seqr-billing', 'anvil-1kg project nåme with uniçøde'),
        ])

    def test_project_page_data(self):
        super(AnvilProjectAPITest, self).test_project_page_data()
        self.mock_list_workspaces.assert_not_called()
        self.assert_no_extra_anvil_calls()

    def test_project_overview(self):
        super(AnvilProjectAPITest, self).test_project_overview()
        self.mock_list_workspaces.assert_not_called()
        self.assert_no_extra_anvil_calls()
        self.mock_get_ws_access_level.assert_called_with(self.collaborator_user, 'my-seqr-billing', 'empty')
        self.assertEqual(self.mock_get_ws_access_level.call_count, 4)

    def test_project_collaborators(self):
        super(AnvilProjectAPITest, self).test_project_collaborators()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_groups.assert_not_called()
        self.mock_get_group_members.assert_not_called()
        self.mock_get_ws_acl.assert_called_with(self.collaborator_user,
                                                'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.assertEqual(self.mock_get_ws_acl.call_count, 3)
        self.mock_get_ws_access_level.assert_called_with(self.collaborator_user,
                                                         'my-seqr-billing',
                                                         'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.assertEqual(self.mock_get_ws_access_level.call_count, 5)
