import json
import mock
from copy import deepcopy
from datetime import datetime
from django.contrib.auth.models import Group
from django.db import connections
from django.urls.base import reverse
import responses

from seqr.models import Project, RnaSeqTpm, RnaSeqSpliceOutlier, RnaSeqOutlier, RnaSample, Family
from seqr.utils.communication_utils import _set_bulk_notification_stream
from seqr.views.apis.project_api import create_project_handler, delete_project_handler, update_project_handler, \
    project_page_data, project_families, project_overview, project_mme_submisssions, project_individuals, \
    project_analysis_groups, update_project_workspace, project_family_notes, project_collaborators, project_locus_lists, \
    project_samples, project_notifications, mark_read_project_notifications, subscribe_project_notifications, \
    update_project_rna_seq, load_rna_seq_sample_data
from seqr.views.apis.data_manager_api_tests import RNA_OUTLIER_SAMPLE_DATA, RNA_OUTLIER_MUSCLE_SAMPLE_GUID, RNA_TPM_SAMPLE_DATA, \
    RNA_TPM_MUSCLE_SAMPLE_GUID, RNA_SPLICE_SAMPLE_DATA, RNA_SPLICE_SAMPLE_GUID, PLACEHOLDER_GUID, \
    RNA_SPLICE_OUTLIER_REQUIRED_COLUMNS,RNA_OUTLIER_REQUIRED_COLUMNS, RNA_TPM_REQUIRED_COLUMNS
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

RNA_DATA_TYPE_PARAMS = {
    'E': {
        'model_cls': RnaSeqOutlier,
        'sample_guid': RNA_OUTLIER_MUSCLE_SAMPLE_GUID,
        'parsed_file_data': RNA_OUTLIER_SAMPLE_DATA,
        'required_columns': RNA_OUTLIER_REQUIRED_COLUMNS,
        'rows': [
            'sampleID\tgeneID\tFDR set\tpValue\tpadjust\tzScore',
            'NA19675_1\tENSG00000240361\tdetail1\t0.01\t0.13\t-3.1',
            'NA19675_1\tENSG00000240361\tdetail2\t0.01\t0.13\t-3.1',
            'NA19675_1\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8',
            'NA21234\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8',
            'HG00731\tENSG00000240361\t\t0.04\t0.112\t1.9',
            'NA21234\tNOT_A_GENE_ID1\tdetail1\t0.064\t0.0000057\t7.8',
            'NA21234\t\tdetail1\t0.064\t0.0000057\t7.8',
        ],
        'message_data_type': 'Expression Outlier',
    },
    'T': {
        'model_cls': RnaSeqTpm,
        'sample_guid': RNA_TPM_MUSCLE_SAMPLE_GUID,
        'parsed_file_data': RNA_TPM_SAMPLE_DATA,
        'required_columns': RNA_TPM_REQUIRED_COLUMNS,
        'mismatch_field': 'tpm',
        'rows': [
            'Name\tDescription\tNA19675_1',
            'ENSG00000240361\tsome gene of interest\t7.8',
            'ENSG00000233750\t\t0.0',
            'NOT_A_GENE_ID1\t\t0.064',
            '\t\t0.064',
        ],
        'message_data_type': 'Expression',
    },
    'S': {
        'model_cls': RnaSeqSpliceOutlier,
        'sample_guid': RNA_SPLICE_SAMPLE_GUID,
        'parsed_file_data': RNA_SPLICE_SAMPLE_DATA,
        'required_columns': RNA_SPLICE_OUTLIER_REQUIRED_COLUMNS,
        'row_id': 'ENSG00000233750-2-167254166-167258349-*-psi3',
        'rows': [
            'hgncSymbol\tseqnames\tstart\tend\tstrand\tsampleID\ttype\tpValue\tpadjust\tdeltaPsi\tcounts\tmeanCounts\ttotalCounts\tmeanTotalCounts\tnonsplitCounts',
            'ENSG00000233750;ENSG00000240361\tchr2\t167254166\t167258349\t*\tNA19675_1\tpsi3\t1.56E-25\t-4.9\t-0.46\t166\t16.6\t1660\t1.66\t1',
            'ENSG00000240361\tchr7\t132885746\t132975168\t*\tNA19675_1\tpsi5\t1.08E-56\t-6.53\t-0.85\t231\t0.231\t2313\t231.3\t1',
            'ENSG00000233750\tchr2\t167258096\t167258349\t*\tNA21234\tpsi3\t1.56E-25\t6.33\t0.45\t143\t14.3\t1433\t143.3\t1',
            '\tchr2\t167258096\t167258349\t*\tHG00731\tpsi3\t1.56E-25\t6.33\t0.45\t143\t14.3\t1433\t143.3\t1',
            'NOT_A_GENE_ID1\tchr2\t167258096\t167258349\t*\tNA21234\tpsi3\t1.56E-25\t6.33\t0.45\t143\t14.3\t1433\t143.3\t1',
            '\tchr2\t167258096\t167258349\t*\tNA19675_1\tpsi3\t1.56E-25\t6.33\t0.45\t143\t14.3\t1433\t143.3\t1',
        ],
        'message_data_type': 'Splice Outlier',
    }
}


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
            f"{self.AIRTABLE_TRACKING_URL}?fields[]=Status&pageSize=100&filterByFormula=AND({{AnVIL Project URL}}='/project/{project_guid}/project_page',OR(Status='Available in Seqr',Status='Loading',Status='Loading Requested',Status='Loading request canceled'))",
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
            'RNA__S': [{'familyCounts': {'F000001_1': 2}, 'loadedDate': '2017-02-05'}],
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

        response_keys = {'familiesByGuid', 'genesById'}

        empty_url = reverse(project_families, args=[EMPTY_PROJECT_GUID])
        self._check_empty_project(empty_url, response_keys)

        self._assert_expected_project_families(url, response_keys)

    def _assert_expected_project_families(self, url, response_keys, no_discovery_tags=False):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), response_keys)

        family_1 = response_json['familiesByGuid']['F000001_1']
        family_3 = response_json['familiesByGuid']['F000003_3']
        empty_family = response_json['familiesByGuid']['F000013_13']
        family_fields = {
            'individualGuids', 'discoveryGeneIds', 'caseReviewStatuses', 'caseReviewStatusLastModified', 'hasRequiredMetadata',
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


        self.assertListEqual(family_3['discoveryGeneIds'], [])
        self.assertListEqual(empty_family['discoveryGeneIds'], [])
        self.assertListEqual(family_1['discoveryGeneIds'], ['ENSG00000135953'])
        family_2_tags = [] if no_discovery_tags else ['ENSG00000135953']
        self.assertListEqual(response_json['familiesByGuid']['F000002_2']['discoveryGeneIds'], family_2_tags)
        no_discovery_families = set(response_json['familiesByGuid'].keys()) - {'F000001_1', 'F000002_2'}
        self.assertSetEqual({
            len(response_json['familiesByGuid'][family_guid]['discoveryGeneIds']) for family_guid in no_discovery_families
        }, {0})

        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000135953'})

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

    def test_update_project_rna_outlier(self):
        self._test_update_project_rna('E', **RNA_DATA_TYPE_PARAMS['E'])

    def test_update_project_rna_tpm(self):
        self._test_update_project_rna('T', **RNA_DATA_TYPE_PARAMS['T'], single_sample_file=True)

    def test_update_project_rna_splice_outlier(self):
        kwargs = {
            **RNA_DATA_TYPE_PARAMS['S'],
            'tissue': 'F',
            'allow_missing_gene': True,
        }
        # Parsed data does not include optional internal-only columns
        internal_cols =  {'rare_disease_samples_total', 'rare_disease_samples_with_this_junction'}
        kwargs['parsed_file_data'] = {
            sample_guid: '\n'.join([
                json.dumps({k: v.replace('e', 'E') for k, v in json.loads(row).items() if k not in internal_cols})
                for row in data.split('\n') if row]
            ) + '\n' for sample_guid, data in kwargs['parsed_file_data'].items()
        }

        self._test_update_project_rna('S', **kwargs)

    @mock.patch('seqr.utils.communication_utils.BASE_URL', 'https://test-seqr.org/')
    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    @mock.patch('seqr.views.utils.file_utils.tempfile.gettempdir', lambda: 'tmp/')
    @mock.patch('seqr.views.utils.dataset_utils.datetime')
    @mock.patch('seqr.utils.communication_utils.send_html_email')
    @mock.patch('seqr.utils.communication_utils.safe_post_to_slack')
    @mock.patch('seqr.views.utils.dataset_utils.os')
    @mock.patch('seqr.utils.file_utils.gzip.open')
    @mock.patch('seqr.utils.file_utils.os.path.isfile')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def _test_update_project_rna(self, data_type, mock_subprocess, mock_does_file_exist, mock_open, mock_os,
                                 mock_send_slack, mock_send_email, mock_datetime, sample_guid=None, model_cls=None,
                                 rows=None, parsed_file_data=None, required_columns=None,  allow_missing_gene=False,
                                 tissue='M', message_data_type=None, single_sample_file=False, **kwargs):
        mock_datetime.now.return_value = datetime(2025, 4, 15)
        mock_os.path.join.side_effect = lambda *args: '/'.join(args)
        initial_model_count = model_cls.objects.count()
        initial_sample_model_count = model_cls.objects.filter(sample__guid=sample_guid).count()

        self.check_pm_login(reverse(update_project_rna_seq, args=[DEMO_PROJECT_GUID]))
        url = reverse(update_project_rna_seq, args=[PROJECT_GUID])
        self.login_manager()

        # Test errors
        file = f'{self.TEMP_DIR}/new_samples.tsv.gz'
        body = {'dataType': data_type, 'file': file, 'tissue': tissue}
        self._set_file_not_found(file, mock_subprocess, mock_does_file_exist, mock_open)
        self.reset_logs()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': f'File not found: {file}'})

        self._set_file_iter([], mock_subprocess, mock_does_file_exist, mock_open)
        invalid_file_ext = file.replace('tsv.gz', 'xlsx')
        invalid_body = {**body, 'file': invalid_file_ext}
        response = self.client.post(url, content_type='application/json', data=json.dumps(invalid_body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': f'Unexpected iterated file type: {invalid_file_ext}'})

        self._set_file_iter([''], mock_subprocess, mock_does_file_exist, mock_open)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': f'Invalid file: missing column(s): {required_columns}'})

        error_rows = [rows[0].replace('NA19675_1', 'NA21234')] + rows[1:] if single_sample_file else rows
        self._set_file_iter(error_rows, mock_subprocess, mock_does_file_exist, mock_open)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        errors = [
            'Unknown Gene IDs: NOT_A_GENE_ID1',
            'Unable to find matches for the following samples: NA21234',
        ]
        if not allow_missing_gene:
            errors.insert(0, 'Samples missing required "gene_id": NA21234')
        self.assertDictEqual(response.json(), {'warnings': None, 'errors': errors})

        # Test loading new data
        mock_open.reset_mock()
        mock_subprocess.reset_mock()
        self.reset_logs()
        self._set_file_iter(rows[:-2], mock_subprocess, mock_does_file_exist, mock_open)
        body.update({'ignoreExtraSamples': True, 'file': file})

        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        info = [
            f'Parsed {1 if single_sample_file else 3} RNA-seq samples',
            f'Attempted data loading for {1 if single_sample_file else 2} RNA-seq samples',
        ]
        warnings = [] if single_sample_file else ['Skipped loading for the following 1 unmatched samples: NA21234']
        file_path = f'rna_sample_data__{data_type}__2025-04-15T00:00:00'
        response_json = response.json()
        self.assertDictEqual(response_json, {
            'info': info, 'warnings': warnings or [], 'sampleGuids': mock.ANY, 'fileName': file_path,
        })

        # test database models are correct
        self.assertEqual(model_cls.objects.count(), initial_model_count - initial_sample_model_count)
        rna_samples = RnaSample.objects.filter(
            tissue_type=tissue, data_type=data_type, data_source='new_samples.tsv.gz', is_active=False,
        )
        self.assertEqual(rna_samples.count(), 1 if single_sample_file else 2)
        guid_map = {'NA19675_1': rna_samples.get(individual_id=1).guid}
        if not single_sample_file:
            guid_map['HG00731'] = rna_samples.get(individual_id=4).guid
        self.assertSetEqual(set(response_json['sampleGuids']), set(guid_map.values()))

        # test notifications
        mv_command = f'gsutil mv tmp/temp_uploads/{file_path} gs://seqr-scratch-temp/{file_path}'
        subprocess_logs = self._get_expected_read_file_subprocess_calls(
            mock_subprocess, 'new_samples.tsv.gz', additional_command=mv_command,
        )
        self.assert_json_logs(self.manager_user, subprocess_logs + [
            (f'create {1 if single_sample_file else 2} RnaSamples', {'dbUpdate': {
                'dbEntity': 'RnaSample', 'updateType': 'bulk_create',
                'entityIds': response_json['sampleGuids'],
            }}),
            ('update 1 RnaSamples', {'dbUpdate': {
                'dbEntity': 'RnaSample', 'entityIds': [sample_guid],
                'updateType': 'bulk_update', 'updateFields': ['is_active']}}),
            (f'delete {model_cls.__name__}s', {'dbUpdate': {
                'dbEntity': model_cls.__name__, 'numEntities': initial_sample_model_count,
                'parentEntityIds': [sample_guid], 'updateType': 'bulk_delete'}}),
        ] + [
            (info_log, None) for info_log in info] + [
            (warn_log, {'severity': 'WARNING'}) for warn_log in warnings
        ] )

        self.assertEqual(mock_send_slack.call_count, 1)
        new_samples = '' if single_sample_file else '\n```HG00731```'
        mock_send_slack.assert_called_with(
            'seqr-data-loading',
            f'{0 if single_sample_file else 1} new RNA {message_data_type} samples are loaded in <https://test-seqr.org/project/R0001_1kg/project_page|1kg project nåme with uniçøde>{new_samples}',
        )

        self.assertEqual(mock_send_email.call_count, 1)
        project_link = f'<a href=https://test-seqr.org/project/{PROJECT_GUID}/project_page>1kg project nåme with uniçøde</a>'
        mock_send_email.assert_called_with(
            email_body=(
                f'Dear seqr user,\n\nThis is to notify you that data for {0 if single_sample_file else 1} new RNA '
                f'{message_data_type} samples has been loaded in seqr project {project_link}\n\nAll the best,\nThe seqr team'
            ),
            subject=f'New RNA {message_data_type} data available in seqr',
            to=['test_user_manager@test.com'],
            process_message=_set_bulk_notification_stream,
        )

        # test correct file interactions
        open_call_count = 1
        open_calls = [mock.call(f'tmp/temp_uploads/{file_path}/NA19675_1.json.gz', 'at')] + [
            mock.call().write(row + '\n') for row in parsed_file_data[sample_guid].split('\n') if row
        ]
        if not single_sample_file:
            open_call_count += 1
            open_calls += [mock.call(f'tmp/temp_uploads/{file_path}/HG00731.json.gz', 'at')] + [
                mock.call().write(row + '\n') for row in parsed_file_data[PLACEHOLDER_GUID].split('\n') if row
            ]
        if mock_subprocess.call_count == 0:
            open_call_count += 1
            open_calls = [
                mock.call(file, 'r'), mock.call().__enter__(), mock.call().__enter__().__iter__()
            ] + open_calls
        self.assertEqual(mock_open.call_count, open_call_count)
        mock_open.assert_has_calls(open_calls)
        mock_os.rename.assert_has_calls([
            mock.call(f'tmp/temp_uploads/{file_path}/{sample_id}.json.gz', f'tmp/temp_uploads/{file_path}/{sample_guid}.json.gz')
            for sample_id, sample_guid in guid_map.items()
        ], any_order=True)

        # test anvil external project access
        self._set_file_iter([row.replace('NA19675_1', 'NA21234') for row in rows[:2]], mock_subprocess, mock_does_file_exist, mock_open)
        external_project_url = url.replace(PROJECT_GUID, 'R0004_non_analyst_project')
        response = self.client.post(external_project_url, content_type='application/json', data=json.dumps(body))
        if self.CLICKHOUSE_HOSTNAME:
            self.assertEqual(response.status_code, 200)
            mock_send_slack.assert_called_with(
                'anvil-data-loading',
                f'1 new RNA {message_data_type} samples are loaded in <https://test-seqr.org/project/R0004_non_analyst_project/project_page|Non-Analyst Project>',
            )
        else:
            self.assertEqual(response.status_code, 403)

    def test_load_rna_outlier_sample_data(self):
        models = self._test_load_rna_seq_sample_data('E', **RNA_DATA_TYPE_PARAMS['E'])

        expected_models = [
            ('ENSG00000240361', 0.13, 0.01, -3.1), ('ENSG00000233750', 0.0000057, 0.064, 7.8),
        ]
        self.assertEqual(models.count(), len(expected_models))
        self.assertListEqual(list(models.values_list('gene_id', 'p_adjust', 'p_value', 'z_score')), expected_models)

    def test_load_rna_tpm_sample_data(self):
        models = self._test_load_rna_seq_sample_data('T', **RNA_DATA_TYPE_PARAMS['T'])

        expected_models = [('ENSG00000240361', 7.8), ('ENSG00000233750', 0.0)]
        self.assertEqual(models.count(), len(expected_models))
        self.assertListEqual(list(models.values_list('gene_id', 'tpm')), expected_models)

    def test_load_rna_splice_outlier_sample_data(self):
        models = self._test_load_rna_seq_sample_data('S', **RNA_DATA_TYPE_PARAMS['S'])

        expected_models = [
            ('ENSG00000233750', '2', 167254166, 167258349, '*', 'psi3', 1.56e-25, -4.9, -0.46, 166, 1, 20),
            ('ENSG00000240361', '2', 167254166, 167258349, '*', 'psi3', 1.56e-25, -4.9, -0.46, 166, 1, 20),
            ('ENSG00000240361', '7', 132885746, 132975168, '*', 'psi5', 1.08e-56, -6.53, -0.85, 231, 1, 20)
        ]
        self.assertEqual(models.count(), len(expected_models))
        self.assertListEqual(expected_models, list(models.values_list(
            'gene_id', 'chrom', 'start', 'end', 'strand', 'type', 'p_value', 'p_adjust', 'delta_intron_jaccard_index',
            'counts', 'rare_disease_samples_with_this_junction', 'rare_disease_samples_total',
        )))

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    @mock.patch('seqr.utils.file_utils.gzip.open')
    @mock.patch('seqr.utils.file_utils.os.path.isfile')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def _test_load_rna_seq_sample_data(self, data_type, mock_subprocess, mock_does_file_exist, mock_open, mock_pm_group, sample_guid=None, parsed_file_data=None, model_cls=None,  mismatch_field='p_value', row_id=None, **kwargs):
        url = reverse(load_rna_seq_sample_data, args=[sample_guid])
        self.check_manager_login(url)

        model_cls.objects.all().delete()
        self.reset_logs()
        parsed_file_lines = parsed_file_data[sample_guid].strip().split('\n')

        file_name = f'{self.TEMP_DIR}/rna_sample_data__{data_type}__2020-04-15T00:00:00'
        not_found_logs = self._set_file_not_found(
            f'{file_name}/{sample_guid}.json.gz', mock_subprocess, mock_does_file_exist, mock_open,
        )

        body = {'fileName': file_name, 'dataType': data_type}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Data for this sample was not properly parsed. Please re-upload the data'})
        self.assert_json_logs(self.manager_user, [
            ('Loading outlier data for NA19675_1', None),
            *not_found_logs,
            (f'No saved temp data found for {sample_guid} with file prefix {file_name}', {
                'severity': 'ERROR', '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
            }),
        ])

        self._set_file_iter(parsed_file_lines, mock_subprocess, mock_does_file_exist, mock_open)

        self.reset_logs()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})

        models = model_cls.objects.all()
        self.assertSetEqual({model.sample.guid for model in models}, {sample_guid})
        self.assertTrue(all(model.sample.is_active for model in models))

        subprocess_logs = self._get_expected_read_file_subprocess_calls(mock_subprocess, f'{file_name}/{sample_guid}.json.gz')

        self.assert_json_logs(self.manager_user, [
            ('Loading outlier data for NA19675_1', None),
            *subprocess_logs,
            (f'create {model_cls.__name__}s', {'dbUpdate': {
                'dbEntity': model_cls.__name__, 'numEntities': models.count(), 'parentEntityIds': [sample_guid],
                'updateType': 'bulk_create',
            }}),
        ])

        mismatch_row = {**json.loads(parsed_file_lines[0]), mismatch_field: '0.05'}
        self._set_file_iter(parsed_file_lines + [json.dumps(mismatch_row)], mock_subprocess, mock_does_file_exist, mock_open)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'error': f'Error in {sample_guid.split("_", 1)[-1].upper()}: mismatched entries for {row_id or mismatch_row["gene_id"]}'
        })

        # Test manager access to AnVIL external projects
        self._set_file_iter([], mock_subprocess, mock_does_file_exist, mock_open)
        Family.objects.filter(id=1).update(project_id=4)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200 if self.CLICKHOUSE_HOSTNAME else 403)

        # Test PM permission
        Family.objects.filter(id=1).update(project_id=3)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)

        self.login_pm_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)

        self._set_file_iter([], mock_subprocess, mock_does_file_exist, mock_open)
        self.login_data_manager_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)

        mock_pm_group.resolve_expression.return_value = 'project-managers'
        mock_pm_group.__eq__.side_effect = lambda s: s == 'project-managers'
        self._set_file_iter([], mock_subprocess, mock_does_file_exist, mock_open)
        self.login_pm_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)

        return models

    @staticmethod
    def _set_file_not_found(file_name, mock_subprocess, mock_does_file_exist, mock_open):
        mock_does_file_exist.return_value = False
        mock_open.return_value.__enter__.return_value.__iter__.return_value = []
        return []

    @staticmethod
    def _set_file_iter(stdout, mock_subprocess, mock_does_file_exist, mock_open):
        mock_does_file_exist.return_value = True
        file_iter = mock_open.return_value.__enter__.return_value.__iter__
        file_iter.return_value = stdout

    @staticmethod
    def _get_expected_read_file_subprocess_calls(mock_subprocess, file_name, additional_command=None):
        mock_subprocess.assert_not_called()
        return []


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
    TEMP_DIR = '/test/rna_loading'

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
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'clickhouse_saved_variants']
    PROJECT_COLLABORATORS = ANVIL_COLLABORATORS
    PROJECT_COLLABORATOR_GROUPS = None
    HAS_EMPTY_PROJECT = False
    TEMP_DIR = 'gs://seqr-scratch-temp'

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
                'or_filters': {'Status': ['Loading', 'Loading Requested', 'Loading request canceled', 'Available in Seqr']},
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

    def _assert_expected_project_families(self, *args, **kwargs):
        super()._assert_expected_project_families(*args, **kwargs)

        # Test success when clickhouse is unavailable
        self.reset_logs()
        connections['clickhouse'].close()
        super()._assert_expected_project_families(*args, **kwargs, no_discovery_tags=True)
        self.assert_json_logs(None, [
            ("Error loading discovery genes from clickhouse: An error occurred in the current transaction. You can't execute queries until the end of the 'atomic' block.", {
                'severity': 'ERROR',
                '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
            }),
        ])

    @staticmethod
    def _set_file_not_found(file_name, mock_subprocess, mock_does_file_exist, mock_open):
        mock_does_file_exist = mock.MagicMock()
        mock_does_file_exist.stdout = [b'CommandException: One or more URLs matched no objects']
        mock_does_file_exist.wait.return_value = 1
        mock_subprocess.side_effect = [mock_does_file_exist]
        return [
            (f'==> gsutil ls gs://seqr-scratch-temp/{file_name}', None),
            ('CommandException: One or more URLs matched no objects', {'severity': 'WARNING'}),
        ]

    @staticmethod
    def _set_file_iter(stdout, mock_subprocess, mock_does_file_exist, mock_open):
        mock_does_file_exist = mock.MagicMock()
        mock_does_file_exist.wait.return_value = 0
        mock_file_iter = mock.MagicMock()
        mock_file_iter.stdout = [row.encode('utf-8') for row in stdout]
        mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter, mock_does_file_exist]

    @staticmethod
    def _get_expected_read_file_subprocess_calls(mock_subprocess, file_name, additional_command=False):
        commands = [
            f'gsutil ls gs://seqr-scratch-temp/{file_name}',
            f'gsutil cat gs://seqr-scratch-temp/{file_name} | gunzip -c -q - ',
        ]
        mock_subprocess.assert_has_calls([mock.call(cmd, stdout=-1, stderr=-2, shell=True) for cmd in commands])  # nosec
        return [(f'==> {cmd}', None) for cmd in commands]
