import json
import mock
from copy import deepcopy
from datetime import datetime
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.project_api import create_project_handler, delete_project_handler, update_project_handler, \
    project_page_data, project_families, project_overview, project_mme_submisssions, project_individuals, \
    project_analysis_groups
from seqr.views.utils.terra_api_utils import TerraAPIException, TerraRefreshTokenFailedException
from seqr.views.utils.test_utils import AuthenticationTestCase, PROJECT_FIELDS, LOCUS_LIST_FIELDS, SAMPLE_FIELDS, \
    FAMILY_FIELDS, INTERNAL_FAMILY_FIELDS, INTERNAL_INDIVIDUAL_FIELDS, INDIVIDUAL_FIELDS, TAG_TYPE_FIELDS, \
    CASE_REVIEW_FAMILY_FIELDS, FAMILY_NOTE_FIELDS, MATCHMAKER_SUBMISSION_FIELDS, ANALYSIS_GROUP_FIELDS, \
    AnvilAuthenticationTestCase, MixAuthenticationTestCase

PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'
DEMO_PROJECT_GUID = 'R0003_test'

PROJECT_PAGE_RESPONSE_KEYS = {'projectsByGuid'}

class ProjectAPITest(object):

    @mock.patch('seqr.views.apis.project_api.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    def test_create_update_and_delete_project(self):
        create_project_url = reverse(create_project_handler)
        self.check_pm_login(create_project_url)

        # check validation of bad requests
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps({'bad_json': None}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Field(s) "name, genomeVersion" are required')

        # send valid request to create project
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps(
            {'name': 'new_project', 'description': 'new project description', 'genomeVersion': '38'}
        ))
        self.assertEqual(response.status_code, 200)

        # check that project was created
        new_project = Project.objects.get(name='new_project')
        self.assertEqual(new_project.description, 'new project description')
        self.assertEqual(new_project.genome_version, '38')
        self.assertEqual(new_project.created_by, self.pm_user)
        self.assertSetEqual({'analyst-projects'}, {pc.name for pc in new_project.projectcategory_set.all()})

        project_guid = new_project.guid
        self.assertSetEqual(set(response.json()['projectsByGuid'].keys()), {project_guid})

        # update the project
        update_project_url = reverse(update_project_handler, args=[project_guid])
        response = self.client.post(update_project_url, content_type='application/json', data=json.dumps(
            {'description': 'updated project description'}
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['projectsByGuid'][project_guid]['description'], 'updated project description')
        self.assertEqual(Project.objects.get(guid=project_guid).description, 'updated project description')

        # genome version should not update
        response = self.client.post(update_project_url, content_type='application/json', data=json.dumps(
            {'genomeVersion': '37'}
        ))
        self.assertEqual(response.json()['projectsByGuid'][project_guid]['genomeVersion'], '38')
        self.assertEqual(Project.objects.get(guid=project_guid).genome_version, '38')

        # delete the project
        delete_project_url = reverse(delete_project_handler, args=[project_guid])
        response = self.client.post(delete_project_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that project was deleted
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 0)

    @mock.patch('seqr.views.apis.project_api.ANALYST_PROJECT_CATEGORY', None)
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
        self.assertEqual(new_project.created_by, self.super_user)
        self.assertListEqual([], list(new_project.projectcategory_set.all()))

        self.assertSetEqual(set(response.json()['projectsByGuid'].keys()), {new_project.guid})

    def test_project_page_data(self):
        url = reverse(project_page_data, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), PROJECT_PAGE_RESPONSE_KEYS)
        project_fields = set()
        project_fields.update(PROJECT_FIELDS)
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

    def _check_empty_project(self, empty_url, response_keys, project_loaded_key=None):
        response = self.client.get(empty_url)
        if self.HAS_EMPTY_PROJECT:
            self.assertEqual(response.status_code, 200)
            response_json = response.json()
            self.assertSetEqual(set(response_json.keys()), response_keys)
            expected_response = {k: {} for k in response_keys}
            expected_response['projectsByGuid'] = {
                EMPTY_PROJECT_GUID: {project_loaded_key: True}
            } if project_loaded_key else mock.ANY
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
            'projectsByGuid', 'samplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid', 'familyTagTypeCounts',
        }
        self.assertSetEqual(set(response_json.keys()), response_keys)

        project_fields = {
            'collaborators', 'locusListGuids', 'variantTagTypes', 'variantFunctionalTagTypes', 'detailsLoaded',
            'workspaceName', 'workspaceNamespace', 'mmeDeletedSubmissionCount', 'mmeSubmissionCount',
            'analysisGroupsLoaded',
        }
        project_fields.update(PROJECT_FIELDS)
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
        self.assertListEqual(project_response['collaborators'], self.PROJECT_COLLABORATORS)
        self.assertEqual(project_response['mmeSubmissionCount'], 1)
        self.assertEqual(project_response['mmeDeletedSubmissionCount'], 0)

        self.assertSetEqual(set(next(iter(response_json['samplesByGuid'].values())).keys()), SAMPLE_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['locusListsByGuid'].values())).keys()), LOCUS_LIST_FIELDS)
        self.assertSetEqual(
            set(next(iter(response_json['analysisGroupsByGuid'].values())).keys()), ANALYSIS_GROUP_FIELDS
        )
        self.assertDictEqual(response_json['familyTagTypeCounts'],  {
            'F000001_1': {'Review': 1, 'Tier 1 - Novel gene and phenotype': 1},
            'F000002_2': {'Excluded': 1, 'Known gene for phenotype': 1},
        })

        # Test empty project
        empty_url = reverse(project_overview, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys)

        if hasattr(self, 'mock_get_ws_acl'):
            self.mock_get_ws_acl.side_effect = TerraAPIException('AnVIL Error', 400)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error'], 'AnVIL Error')

            self.mock_get_ws_acl.side_effect = TerraRefreshTokenFailedException('Refresh Error')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['error'], '/login')

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.orm_to_json_utils.ANALYST_USER_GROUP', 'analysts')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    def test_project_families(self, mock_analyst_group):
        url = reverse(project_families, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'projectsByGuid', 'familiesByGuid', 'genesById'}
        self.assertSetEqual(set(response_json.keys()), response_keys)

        family_1 = response_json['familiesByGuid']['F000001_1']
        family_fields = {
            'individualGuids', 'discoveryTags', 'caseReviewStatuses', 'caseReviewStatusLastModified', 'hasFeatures',
        }
        family_fields.update(FAMILY_FIELDS)
        self.assertSetEqual(set(family_1.keys()), family_fields)

        self.assertListEqual(family_1['caseReviewStatuses'], ['A', 'I', 'U'])
        self.assertTrue(family_1['hasFeatures'])
        self.assertFalse(response_json['familiesByGuid']['F000003_3']['hasFeatures'])

        self.assertSetEqual({tag['variantGuid'] for tag in family_1['discoveryTags']}, {'SV0000001_2103343353_r0390_100'})
        self.assertSetEqual(
            {tag['variantGuid'] for tag in response_json['familiesByGuid']['F000002_2']['discoveryTags']},
            {'SV0000002_1248367227_r0390_100'})
        no_discovery_families = set(response_json['familiesByGuid'].keys()) - {'F000001_1', 'F000002_2'}
        self.assertSetEqual({
            len(response_json['familiesByGuid'][family_guid]['discoveryTags']) for family_guid in no_discovery_families
        }, {0})

        self.assertDictEqual(response_json['projectsByGuid'], {PROJECT_GUID: {'familiesLoaded': True}})
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000135953'})

        # Test empty project
        empty_url = reverse(project_families, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys, 'familiesLoaded')

        # Test analyst users have internal fields returned
        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        family_fields.update(INTERNAL_FAMILY_FIELDS)
        family_fields.update(CASE_REVIEW_FAMILY_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['familiesByGuid'].values())).keys()), family_fields)


    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.orm_to_json_utils.ANALYST_USER_GROUP', 'analysts')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    def test_project_individuals(self, mock_analyst_group):
        url = reverse(project_individuals, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'projectsByGuid',  'individualsByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertDictEqual(response_json['projectsByGuid'], {PROJECT_GUID: {'individualsLoaded': True}})

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
        self._check_empty_project(empty_url, response_keys, 'individualsLoaded')

        # Test analyst users have internal fields returned
        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(next(iter(response_json['individualsByGuid'].values())).keys()), INTERNAL_INDIVIDUAL_FIELDS)

    def test_project_analysis_groups(self):
        url = reverse(project_analysis_groups, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'projectsByGuid', 'analysisGroupsByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertDictEqual(response_json['projectsByGuid'], {PROJECT_GUID: {'analysisGroupsLoaded': True}})
        self.assertEqual(len(response_json['analysisGroupsByGuid']), 1)
        self.assertSetEqual(
            set(next(iter(response_json['analysisGroupsByGuid'].values())).keys()), ANALYSIS_GROUP_FIELDS
        )

    def test_project_mme_submisssions(self):
        url = reverse(project_mme_submisssions, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'projectsByGuid', 'mmeSubmissionsByGuid', 'familyNotesByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertDictEqual(response_json['projectsByGuid'], {PROJECT_GUID: {'mmeSubmissionsLoaded': True}})
        submission_fields = {'geneIds'}
        submission_fields.update(MATCHMAKER_SUBMISSION_FIELDS)
        self.assertSetEqual(
            set(next(iter(response_json['mmeSubmissionsByGuid'].values())).keys()), submission_fields
        )
        self.assertSetEqual(set(next(iter(response_json['familyNotesByGuid'].values())).keys()), FAMILY_NOTE_FIELDS)

        # Test empty project
        empty_url = reverse(project_mme_submisssions, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys, 'mmeSubmissionsLoaded')


BASE_COLLABORATORS = [
    {'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test Collaborator User',
     'email': 'test_user_collaborator@test.com', 'firstName': 'Test Collaborator User',
     'hasEditPermissions': False, 'hasViewPermissions': True, 'id': 12, 'isActive': True, 'isAnvil': False,
     'isSuperuser': False, 'isAnalyst': False, 'isDataManager': False, 'isPm': False, 'lastLogin': mock.ANY,
     'lastName': '', 'username': 'test_user_collaborator'},
    {'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test Manager User', 'email': 'test_user_manager@test.com',
     'firstName': 'Test Manager User', 'hasEditPermissions': True, 'hasViewPermissions': True, 'id': 11,
     'isActive': True, 'isAnvil': False, 'isAnalyst': False, 'isDataManager': False, 'isPm': False, 'isSuperuser': False,
     'lastLogin': None, 'lastName': '', 'username': 'test_user_manager'}]

ANVIL_COLLABORATORS = [{
    'dateJoined': '', 'displayName': False, 'email': 'test_user_pure_anvil@test.com',
    'firstName': '', 'hasEditPermissions': False, 'hasViewPermissions': True, 'id': '', 'isAnvil': True,
    'isActive': True, 'isAnalyst': False, 'isDataManager': False, 'isPm': False, 'isSuperuser': False, 'lastName': '',
    'lastLogin': '', 'username': 'test_user_pure_anvil@test.com'}] + deepcopy(BASE_COLLABORATORS)
for collab in ANVIL_COLLABORATORS:
    collab['isAnvil'] = True

LOCAL_COLLAB = {
    'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test seqr local User', 'email': 'test_local_user@test.com',
    'firstName': 'Test seqr local User', 'hasEditPermissions': False, 'hasViewPermissions': True, 'id': 14,
    'isActive': True, 'isAnvil': False, 'isSuperuser': False, 'isAnalyst': False, 'isDataManager': False, 'isPm': False,
    'lastLogin': None, 'lastName': '', 'username': 'test_local_user'}

# Tests for AnVIL access disabled
class LocalProjectAPITest(AuthenticationTestCase, ProjectAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']
    PROJECT_COLLABORATORS = BASE_COLLABORATORS
    HAS_EMPTY_PROJECT = True


# Test for permissions from AnVIL only
class AnvilProjectAPITest(AnvilAuthenticationTestCase, ProjectAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    PROJECT_COLLABORATORS = ANVIL_COLLABORATORS
    HAS_EMPTY_PROJECT = False

    def test_create_update_and_delete_project(self):
        super(AnvilProjectAPITest, self).test_create_update_and_delete_project()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_ws_access_level.assert_not_called()

    def test_project_page_data(self):
        super(AnvilProjectAPITest, self).test_project_page_data()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()

    def test_project_overview(self):
        super(AnvilProjectAPITest, self).test_project_overview()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_called_with(self.collaborator_user,
            'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.assertEqual(self.mock_get_ws_acl.call_count, 3)
        self.mock_get_ws_access_level.assert_called_with(self.collaborator_user,
            'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.assertEqual(self.mock_get_ws_access_level.call_count, 7)

# Test for permissions from AnVIL and local
class MixProjectAPITest(MixAuthenticationTestCase, ProjectAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    PROJECT_COLLABORATORS = ANVIL_COLLABORATORS + [LOCAL_COLLAB]
    HAS_EMPTY_PROJECT = True

    def test_create_update_and_delete_project(self):
        super(MixProjectAPITest, self).test_create_update_and_delete_project()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_ws_access_level.assert_not_called()

    def test_project_page_data(self):
        super(MixProjectAPITest, self).test_project_page_data()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()

    def test_project_overview(self):
        super(MixProjectAPITest, self).test_project_overview()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_called_with(self.collaborator_user,
            'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.assertEqual(self.mock_get_ws_acl.call_count, 3)
        self.mock_get_ws_access_level.assert_called_with(self.collaborator_user,
            'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.assertEqual(self.mock_get_ws_access_level.call_count, 4)
