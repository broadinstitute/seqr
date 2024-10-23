import json
import mock
from copy import deepcopy
from datetime import datetime
from django.contrib.auth.models import Group
from django.urls.base import reverse
import responses

from seqr.models import Project
from seqr.views.apis.project_api import create_project_handler, delete_project_handler, update_project_handler, \
    project_page_data, project_families, project_overview, project_mme_submisssions, project_individuals, \
    project_analysis_groups, update_project_workspace, project_family_notes, project_collaborators, project_locus_lists, \
    project_samples, project_notifications, mark_read_project_notifications, subscribe_project_notifications
from seqr.views.utils.terra_api_utils import TerraAPIException, TerraRefreshTokenFailedException
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, \
    PROJECT_FIELDS, LOCUS_LIST_FIELDS, PA_LOCUS_LIST_FIELDS, NO_INTERNAL_CASE_REVIEW_INDIVIDUAL_FIELDS, \
    SAMPLE_FIELDS, SUMMARY_FAMILY_FIELDS, INTERNAL_INDIVIDUAL_FIELDS, INDIVIDUAL_FIELDS, TAG_TYPE_FIELDS, \
    FAMILY_NOTE_FIELDS, MATCHMAKER_SUBMISSION_FIELDS, ANALYSIS_GROUP_FIELDS, \
    EXT_WORKSPACE_NAMESPACE, TEST_EMPTY_PROJECT_WORKSPACE, DYNAMIC_ANALYSIS_GROUP_FIELDS

PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'
DEMO_PROJECT_GUID = 'R0003_test'

PROJECT_PAGE_RESPONSE_KEYS = {'projectsByGuid'}

BASE_CREATE_PROJECT_JSON = {
    'name': 'new_project', 'description': 'new project description', 'genomeVersion': '38', 'isDemo': True,
    'disableMme': True, 'consentCode': 'H',
}
WORKSPACE_JSON = {'workspaceName': TEST_EMPTY_PROJECT_WORKSPACE, 'workspaceNamespace': EXT_WORKSPACE_NAMESPACE}
WORKSPACE_CREATE_PROJECT_JSON = deepcopy(WORKSPACE_JSON)
WORKSPACE_CREATE_PROJECT_JSON.update(BASE_CREATE_PROJECT_JSON)

MOCK_GROUP_UUID = '123abd'

MOCK_AIRTABLE_URL = 'http://testairtable'
MOCK_RECORDS = {'records': [
    {'id': 'recH4SEO1CeoIlOiE', 'fields': {'Status': 'Loading'}},
    {'id': 'recSgwrXNkmlIB5eM', 'fields': {'Status': 'Available in Seqr'}},
]}


class ProjectAPITest(object):
    CREATE_PROJECT_JSON = WORKSPACE_CREATE_PROJECT_JSON
    REQUIRED_FIELDS = ['name', 'genomeVersion', 'workspaceNamespace', 'workspaceName']
    AIRTABLE_TRACKING_URL = f'{MOCK_AIRTABLE_URL}/appUelDNM3BnWaR7M/AnVIL%20Seqr%20Loading%20Requests%20Tracking'

    @mock.patch('seqr.views.utils.airtable_utils.logger')
    @mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_URL', MOCK_AIRTABLE_URL)
    @mock.patch('seqr.models.uuid.uuid4', lambda: MOCK_GROUP_UUID)
    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    @responses.activate
    def test_create_and_delete_project(self, mock_airtable_logger):
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
        self.assertEqual(new_project.created_by, self.pm_user)
        self.assertEqual(new_project.projectcategory_set.count(), 0)
        expected_workspace_name = self.CREATE_PROJECT_JSON.get('workspaceName')
        self.assertDictEqual({k: getattr(new_project, k) for k in new_project._meta.json_fields}, {
            'guid': mock.ANY,
            'name': 'new_project',
            'description': 'new project description',
            'workspace_namespace': self.CREATE_PROJECT_JSON.get('workspaceNamespace'),
            'workspace_name': expected_workspace_name,
            'has_case_review': False,
            'enable_hgmd': False,
            'is_demo': True,
            'all_user_demo': False,
            'consent_code': 'H',
            'created_date': mock.ANY,
            'last_modified_date': mock.ANY,
            'last_accessed_date': mock.ANY,
            'genome_version': '38',
            'is_mme_enabled': False,
            'mme_contact_institution': 'Broad Center for Mendelian Genomics',
            'mme_primary_data_owner': 'Samantha Baxter',
            'mme_contact_url': 'mailto:matchmaker@broadinstitute.org',
            'vlm_contact_email': 'vlm@broadinstitute.org',
        })
        self._check_created_project_groups(new_project)

        project_guid = new_project.guid
        self.assertSetEqual(set(response.json()['projectsByGuid'].keys()), {project_guid})
        self.assertTrue(response.json()['projectsByGuid'][project_guid]['userIsCreator'])

        # delete the project
        responses.add(
            responses.GET,
            f"{self.AIRTABLE_TRACKING_URL}?fields[]=Status&pageSize=100&filterByFormula=AND({{AnVIL Project URL}}='/project/{project_guid}/project_page',OR(Status='Available in Seqr',Status='Loading',Status='Loading Requested'))",
            json=MOCK_RECORDS)
        responses.add(responses.PATCH, self.AIRTABLE_TRACKING_URL, status=400)
        delete_project_url = reverse(delete_project_handler, args=[project_guid])
        response = self.client.post(delete_project_url, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # check that project was deleted
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 0)
        self.assertEqual(
            Group.objects.filter(name__in=['new_project_can_edit_123abd', 'new_project_can_view_123abd']).count(), 0,
        )

        self._assert_expected_airtable_requests(mock_airtable_logger)

    def _check_created_project_groups(self, project):
        self.assertEqual(project.subscribers.name, 'new_project_subscribers_123abd')
        self.assertSetEqual(set(project.subscribers.user_set.all()), {self.pm_user})

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

        self.assertEqual(response_json['workspaceName'], TEST_EMPTY_PROJECT_WORKSPACE)
        self.assertEqual(response_json['workspaceNamespace'], EXT_WORKSPACE_NAMESPACE)
        self.assertEqual(response_json['genomeVersion'], '37')
        self.assertNotEqual(response_json['description'], 'updated project description')

        project = Project.objects.get(guid=PROJECT_GUID)
        self.assertEqual(project.workspace_name, TEST_EMPTY_PROJECT_WORKSPACE)
        self.assertEqual(project.workspace_namespace, EXT_WORKSPACE_NAMESPACE)

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
            'variantTagTypes', 'variantFunctionalTagTypes', 'sampleCounts',
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
        self.assertDictEqual(project_response['sampleCounts'], {
            'WES__SNV_INDEL': [{
                'familyCounts': {
                    'F000001_1': 3, 'F000002_2': 3, 'F000003_3': 1, 'F000004_4': 1, 'F000005_5': 1, 'F000006_6': 1,
                    'F000007_7': 1, 'F000008_8': 1, 'F000010_10': 1,
                },
                'loadedDate': '2017-02-05',
            }],
            'WES__SV': [{'familyCounts': {'F000002_2': 3}, 'loadedDate': '2018-02-05'}],
            'WES__MITO': [{'familyCounts': {'F000002_2': 1}, 'loadedDate': '2022-02-05'}],
            'RNA__S': [{'familyCounts': {'F000001_1': 3}, 'loadedDate': '2017-02-05'}],
            'RNA__T': [{'familyCounts': {'F000001_1': 2}, 'loadedDate': '2017-02-05'}],
            'RNA__E': [{'familyCounts': {'F000001_1': 1}, 'loadedDate': '2017-02-05'}],
        })
        self.assertEqual(project_response['mmeSubmissionCount'], 1)
        self.assertEqual(project_response['mmeDeletedSubmissionCount'], 0)

        self.assertEqual(len(response_json['samplesByGuid']), 16)
        self.assertSetEqual(set(next(iter(response_json['samplesByGuid'].values())).keys()), SAMPLE_FIELDS)
        self.assertDictEqual(response_json['familyTagTypeCounts'],  {
            'F000001_1': {'Review': 1, 'Tier 1 - Novel gene and phenotype': 1, 'MME Submission': 1},
            'F000002_2': {'AIP': 1, 'Excluded': 1, 'Known gene for phenotype': 1},
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
        empty_family = response_json['familiesByGuid']['F000013_13']
        family_fields = {
            'individualGuids', 'discoveryTags', 'caseReviewStatuses', 'caseReviewStatusLastModified', 'hasRequiredMetadata',
            'parents', 'hasPhenotypePrioritization', 'hasRna', 'externalData',
        }
        family_fields.update(SUMMARY_FAMILY_FIELDS)
        self.assertSetEqual(set(family_1.keys()), family_fields)
        self.assertSetEqual(set(empty_family.keys()), family_fields)

        self.assertEqual(len(family_1['individualGuids']), 3)
        self.assertEqual(len(family_3['individualGuids']), 1)
        self.assertEqual(len(empty_family['individualGuids']), 0)
        self.assertListEqual(family_1['caseReviewStatuses'], ['A', 'I', 'U'])
        self.assertListEqual(family_3['caseReviewStatuses'], [])
        self.assertListEqual(empty_family['caseReviewStatuses'], [])
        self.assertEqual(family_1['caseReviewStatusLastModified'], '2017-03-12T22:34:49.964Z')
        self.assertIsNone(family_3['caseReviewStatusLastModified'])
        self.assertIsNone(empty_family['caseReviewStatusLastModified'])
        self.assertTrue(family_1['hasRequiredMetadata'])
        self.assertFalse(family_3['hasRequiredMetadata'])
        self.assertFalse(empty_family['hasRequiredMetadata'])
        self.assertListEqual(family_1['parents'], [{'maternalGuid': 'I000003_na19679', 'paternalGuid': 'I000002_na19678', 'individualGuid': 'I000001_na19675'}])
        self.assertListEqual(family_3['parents'], [])
        self.assertListEqual(empty_family['parents'], [])
        self.assertEqual(family_1['hasPhenotypePrioritization'], True)
        self.assertFalse(family_3['hasPhenotypePrioritization'], False)
        self.assertFalse(empty_family['hasPhenotypePrioritization'], False)
        self.assertEqual(family_1['hasRna'], True)
        self.assertFalse(family_3['hasRna'], False)
        self.assertFalse(empty_family['hasRna'], False)
        self.assertListEqual(family_1['externalData'], ['M'])
        self.assertListEqual(family_3['externalData'], [])
        self.assertListEqual(empty_family['externalData'], [])


        self.assertListEqual(family_3['discoveryTags'], [])
        self.assertListEqual(empty_family['discoveryTags'], [])
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

    def test_project_samples(self):
        url = reverse(project_samples, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'samplesByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)

        self.assertEqual(len(response_json['samplesByGuid']), 17)
        self.assertSetEqual(set(next(iter(response_json['samplesByGuid'].values())).keys()), SAMPLE_FIELDS)

        # Test empty project
        empty_url = reverse(project_samples, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys)

    def test_project_analysis_groups(self):
        url = reverse(project_analysis_groups, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        response_keys = {'analysisGroupsByGuid'}
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertEqual(len(response_json['analysisGroupsByGuid']), 4)
        self.assertSetEqual(
            set(response_json['analysisGroupsByGuid']['AG0000183_test_group'].keys()), ANALYSIS_GROUP_FIELDS
        )
        self.assertSetEqual(
            set(response_json['analysisGroupsByGuid']['DAG0000002_my_new_cases'].keys()), DYNAMIC_ANALYSIS_GROUP_FIELDS
        )

        response = self.client.get(url.replace(PROJECT_GUID, DEMO_PROJECT_GUID))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'analysisGroupsByGuid': {'DAG0000001_unsolved': {
            'analysisGroupGuid': 'DAG0000001_unsolved', 'projectGuid': None, 'name': 'Unsolved',
            'criteria': {'firstSample': ['SHOW_DATA_LOADED'], 'analysisStatus': ['I', 'P', 'C', 'Rncc', 'Rcpc']},
        }}})

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

    @mock.patch('django.contrib.humanize.templatetags.humanize.datetime')
    def test_project_notifications(self, mock_datetime):
        mock_datetime.now.return_value = datetime.fromisoformat('2024-01-01 00:00:00+00:00')
        unread_url = reverse(project_notifications, args=[PROJECT_GUID, 'unread'])
        self.check_collaborator_login(unread_url)

        # Do not allow arbitrary read status
        response = self.client.get(unread_url+'s')
        self.assertEqual(response.status_code, 404)

        # Non-subscribers do not necessarily have notification models for all new notifications
        self.assertEqual(self.collaborator_user.notifications.count(), 1)

        response = self.client.get(unread_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'isSubscriber': False,
            'readCount': 0,
            'unreadNotifications': [
                {'timestamp': '2 weeks ago', 'id': 4, 'verb': 'Loaded 2 new WES SV samples'},
                {'timestamp': '4 months ago', 'id': 3, 'verb': 'Loaded 8 new WES samples'},
            ],
        })

        # Notification models will have been created for the non-subscriber for any new notifications
        self.assertEqual(self.collaborator_user.notifications.count(), 2)

        # Notifications only show for the correct project
        response = self.client.get(reverse(project_notifications, args=[DEMO_PROJECT_GUID, 'unread']))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'isSubscriber': False,
            'readCount': 0,
            'unreadNotifications': [],
        })

        # Test subscribers
        self.login_manager()
        response = self.client.get(unread_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'isSubscriber': True,
            'readCount': 1,
            'unreadNotifications': [{'timestamp': '2 weeks ago', 'id': 1, 'verb': 'Loaded 2 new WES SV samples'}],
        })

        read_url = reverse(project_notifications, args=[PROJECT_GUID, 'read'])
        response = self.client.get(read_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'isSubscriber': True,
            'readNotifications': [{'timestamp': '4 months ago', 'id': 2, 'verb': 'Loaded 8 new WES samples'}],
        })

    def test_mark_read_project_notifications(self):
        url = reverse(mark_read_project_notifications, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'readCount': 1, 'unreadNotifications': []})
        self.assertEqual(self.collaborator_user.notifications.filter(unread=True).count(), 0)

        # Test subscribers
        self.login_manager()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'readCount': 2, 'unreadNotifications': []})
        self.assertEqual(self.manager_user.notifications.filter(unread=True).count(), 0)

    def test_subscribe_project_notifications(self):
        url = reverse(subscribe_project_notifications, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'isSubscriber': True})
        self.assertTrue(self.collaborator_user.groups.filter(name='subscribers').exists())


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
        super()._check_created_project_groups(project)
        self.assertEqual(project.can_edit_group.name, 'new_project_can_edit_group_123abd')
        self.assertEqual(project.can_view_group.name, 'new_project_can_view_group_123abd')
        self.assertSetEqual(set(project.can_edit_group.user_set.all()), {self.pm_user})
        self.assertSetEqual(set(project.can_view_group.user_set.all()), {self.pm_user})

    def test_update_project_workspace(self):
        url = reverse(update_project_workspace, args=[PROJECT_GUID])
        # For non-AnVIL seqr, updating workspace should always fail
        self.login_pm_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps(WORKSPACE_JSON))
        self.assertEqual(response.status_code, 403)

    def _assert_expected_airtable_requests(self, *args, **kwargs):
        self.assertEqual(len(responses.calls), 0)


# Test for permissions from AnVIL only
class AnvilProjectAPITest(AnvilAuthenticationTestCase, ProjectAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    PROJECT_COLLABORATORS = ANVIL_COLLABORATORS
    PROJECT_COLLABORATOR_GROUPS = None
    HAS_EMPTY_PROJECT = False

    def test_create_and_delete_project(self, *args, **kwargs):
        super(AnvilProjectAPITest, self).test_create_and_delete_project(*args, **kwargs)
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_group_members.assert_not_called()
        self.mock_get_groups.assert_has_calls([
            mock.call(self.collaborator_user), mock.call(self.manager_user), mock.call(self.analyst_user),
            mock.call(self.pm_user)])
        self.mock_get_ws_access_level.assert_has_calls([
            mock.call(self.pm_user, 'bar', 'foo'),
            mock.call(self.pm_user, 'ext-data', 'empty'),
        ])

    def _assert_expected_airtable_requests(self, mock_airtable_logger):
        self.assertEqual(responses.calls[1].request.url, self.AIRTABLE_TRACKING_URL)
        self.assertEqual(responses.calls[1].request.method, 'PATCH')
        self.assertDictEqual(json.loads(responses.calls[1].request.body), {'records': [
            {'id': 'recH4SEO1CeoIlOiE', 'fields': {'Status': 'Project Deleted'}},
            {'id': 'recSgwrXNkmlIB5eM', 'fields': {'Status': 'Project Deleted'}},
        ]})

        mock_airtable_logger.error.assert_called_with(
            'Airtable patch "AnVIL Seqr Loading Requests Tracking" error: 400 Client Error: Bad Request for url: http://testairtable/appUelDNM3BnWaR7M/AnVIL%20Seqr%20Loading%20Requests%20Tracking',
            self.pm_user, detail={
                'or_filters': {'Status': ['Loading', 'Loading Requested', 'Available in Seqr']},
                'and_filters': {'AnVIL Project URL': '/project/R0005_new_project/project_page'},
                'update': {'Status': 'Project Deleted'}})

    def _check_created_project_groups(self, project):
        super()._check_created_project_groups(project)
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
        self.mock_get_ws_access_level.assert_called_with(self.collaborator_user, 'ext-data', 'empty')
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
