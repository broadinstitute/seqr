import json
import mock
from datetime import datetime
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.project_api import create_project_handler, delete_project_handler, update_project_handler, \
    project_page_data
from seqr.views.utils.test_utils import AuthenticationTestCase, PROJECT_FIELDS, LOCUS_LIST_FIELDS, IGV_SAMPLE_FIELDS, \
    FAMILY_FIELDS, INTERNAL_FAMILY_FIELDS, INTERNAL_INDIVIDUAL_FIELDS, INDIVIDUAL_FIELDS, SAMPLE_FIELDS,\
    AnvilAuthenticationTestCase, MixAuthenticationTestCase

PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'


class ProjectAPITest(object):
    multi_db = True

    def test_create_update_and_delete_project(self):
        create_project_url = reverse(create_project_handler)
        self.check_require_login(create_project_url)

        # check validation of bad requests
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps({'bad_json': None}))
        self.assertEqual(response.status_code, 400)

        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps({'form': {'missing_name': True}}))
        self.assertEqual(response.status_code, 400)

        # send valid request to create project
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps(
            {'name': 'new_project', 'description': 'new project description', 'genomeVersion': '38'}
        ))
        self.assertEqual(response.status_code, 200)

        # check that project was created
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 1)
        self.assertEqual(new_project[0].description, 'new project description')
        self.assertEqual(new_project[0].genome_version, '38')

        project_guid = new_project[0].guid
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

    def test_project_page_data(self):
        url = reverse(project_page_data, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid', 'locusListsByGuid',
             'analysisGroupsByGuid', 'genesById', 'mmeSubmissionsByGuid', 'igvSamplesByGuid'}
        )
        self.assertSetEqual(
            set(response_json['projectsByGuid'][PROJECT_GUID]['variantTagTypes'][0].keys()),
            {'variantTagTypeGuid', 'name', 'category', 'description', 'color', 'order', 'numTags', 'numTagsPerFamily'}
        )
        project_fields = {
            'collaborators', 'locusListGuids', 'variantTagTypes', 'variantFunctionalTagTypes', 'detailsLoaded',
            'discoveryTags', 'workspaceName', 'workspaceNamespace'
        }
        project_fields.update(PROJECT_FIELDS)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), project_fields)
        self.assertEqual(
            response_json['projectsByGuid'][PROJECT_GUID]['lastAccessedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )
        self.assertListEqual(response_json['projectsByGuid'][PROJECT_GUID]['collaborators'], self.PROJECT_COLLABORATORS)
        discovery_tags = response_json['projectsByGuid'][PROJECT_GUID]['discoveryTags']
        self.assertEqual(len(discovery_tags), 2)
        self.assertSetEqual(
            {tag['variantGuid'] for tag in discovery_tags},
            {'SV0000001_2103343353_r0390_100', 'SV0000002_1248367227_r0390_100'})
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000135953', 'ENSG00000186092'})
        family_fields = {'individualGuids'}
        family_fields.update(FAMILY_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['familiesByGuid'].values())).keys()), family_fields)
        individual_fields = {'sampleGuids', 'igvSampleGuids', 'mmeSubmissionGuid'}
        individual_fields.update(INDIVIDUAL_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['individualsByGuid'].values())).keys()), individual_fields)
        self.assertSetEqual(set(next(iter(response_json['samplesByGuid'].values())).keys()), SAMPLE_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['igvSamplesByGuid'].values())).keys()), IGV_SAMPLE_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['locusListsByGuid'].values())).keys()), LOCUS_LIST_FIELDS)
        self.assertSetEqual(
            set(next(iter(response_json['analysisGroupsByGuid'].values())).keys()),
            {'analysisGroupGuid', 'description', 'name', 'projectGuid', 'familyGuids'}
        )
        self.assertSetEqual(
            set(next(iter(response_json['mmeSubmissionsByGuid'].values())).keys()),
            {'submissionGuid', 'individualGuid', 'createdDate', 'lastModifiedDate', 'deletedDate', 'geneIds'}
        )
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000001_na19675']['features'][0].keys()),
            {'id', 'category', 'label'}
        )
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000001_na19675']['absentFeatures'][0].keys()),
            {'id', 'category', 'label'}
        )

        # Test staff users have internal fields returned
        self.login_staff_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        family_fields.update(INTERNAL_FAMILY_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['familiesByGuid'].values())).keys()), family_fields)
        individual_fields.update(INTERNAL_INDIVIDUAL_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['individualsByGuid'].values())).keys()), individual_fields)

        # Test invalid project guid
        invalid_url = reverse(project_page_data, args=['FAKE_GUID'])
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'Project matching query does not exist.')

    def test_empty_project_page_data(self):
        url = reverse(project_page_data, args=[EMPTY_PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid', 'locusListsByGuid',
             'analysisGroupsByGuid', 'genesById', 'mmeSubmissionsByGuid', 'igvSamplesByGuid'}
        )
        self.assertListEqual(list(response_json['projectsByGuid'].keys()), [EMPTY_PROJECT_GUID])
        self.assertDictEqual(response_json['familiesByGuid'], {})
        self.assertDictEqual(response_json['individualsByGuid'], {})
        self.assertDictEqual(response_json['samplesByGuid'], {})
        self.assertDictEqual(response_json['analysisGroupsByGuid'], {})
        self.assertDictEqual(response_json['genesById'], {})
        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {})
        self.assertDictEqual(response_json['locusListsByGuid'], {})


# Tests for AnVIL access disabled
class LocalProjectAPITest(AuthenticationTestCase, ProjectAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']
    PROJECT_COLLABORATORS = [{'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test Manager User',
                              'email': 'test_user_manager@test.com', 'firstName': 'Test Manager User',
                              'hasEditPermissions': True, 'hasViewPermissions': True, 'id': 11, 'isActive': True, 'isAnvil': False,
                              'isStaff': False, 'lastLogin': None, 'lastName': '', 'username': 'test_user_manager'},
                             {'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test Non Staff User',
                              'email': 'test_user_no_staff@test.com', 'firstName': 'Test Non Staff User',
                              'hasEditPermissions': False, 'hasViewPermissions': True, 'id': 12, 'isActive': True, 'isAnvil': False,
                              'isStaff': False, 'lastLogin': mock.ANY, 'lastName': '',
                              'username': 'test_user_non_staff'}]


# Test for permissions from AnVIL only
class AnvilProjectAPITest(AnvilAuthenticationTestCase, ProjectAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    PROJECT_COLLABORATORS = [{'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test Manager User',
                              'email': 'test_user_manager@test.com', 'firstName': 'Test Manager User',
                              'hasEditPermissions': False, 'hasViewPermissions': True, 'id': 11, 'isActive': True, 'isAnvil': True,
                              'isStaff': False, 'lastLogin': None, 'lastName': '', 'username': 'test_user_manager'},
                             {'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test Non Staff User',
                              'email': 'test_user_no_staff@test.com', 'firstName': 'Test Non Staff User',
                              'hasEditPermissions': False, 'hasViewPermissions': True, 'id': 12, 'isActive': True, 'isAnvil': True,
                              'isStaff': False, 'lastLogin': mock.ANY, 'lastName': '', 'username': 'test_user_non_staff'}]

    def test_create_update_and_delete_project(self):
        super(AnvilProjectAPITest, self).test_create_update_and_delete_project()
        self.mock_list_workspaces.assert_not_called()
        self.mock_service_account.get.assert_not_called()

    def test_project_page_data(self):
        super(AnvilProjectAPITest, self).test_project_page_data()
        self.mock_list_workspaces.assert_not_called()
        self.mock_service_account.get.assert_called_with(
            'api/workspaces/my-seqr-billing/anvil-1kg project n\u00e5me with uni\u00e7\u00f8de/acl')
        self.assertEqual(self.mock_service_account.get.call_count, 5)

    def test_empty_project_page_data(self):
        url = reverse(project_page_data, args=[EMPTY_PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


# Test for permissions from AnVIL and local
class MixProjectAPITest(MixAuthenticationTestCase, ProjectAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']
    PROJECT_COLLABORATORS = [{'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test Manager User',
                              'email': 'test_user_manager@test.com', 'firstName': 'Test Manager User',
                              'hasEditPermissions': False, 'hasViewPermissions': True, 'id': 11, 'isActive': True, 'isAnvil': True,
                              'isStaff': False, 'lastLogin': None, 'lastName': '', 'username': 'test_user_manager'},
                             {'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test Non Staff User',
                              'email': 'test_user_no_staff@test.com', 'firstName': 'Test Non Staff User',
                              'hasEditPermissions': False, 'hasViewPermissions': True, 'id': 12, 'isActive': True, 'isAnvil': True,
                              'isStaff': False, 'lastLogin': mock.ANY, 'lastName': '', 'username': 'test_user_non_staff'},
                             {'dateJoined': '2017-03-12T23:09:54.180Z', 'displayName': 'Test seqr local User',
                              'email': 'test_local_user@test.com', 'firstName': 'Test seqr local User',
                              'hasEditPermissions': False, 'hasViewPermissions': True, 'id': 14, 'isActive': True, 'isAnvil': False,
                              'isStaff': False, 'lastLogin': None, 'lastName': '', 'username': 'test_local_user'}
                             ]

    def test_create_update_and_delete_project(self):
        super(MixProjectAPITest, self).test_create_update_and_delete_project()
        self.mock_list_workspaces.assert_not_called()
        self.mock_service_account.get.assert_not_called()

    def test_project_page_data(self):
        super(MixProjectAPITest, self).test_project_page_data()
        self.mock_list_workspaces.assert_not_called()
        self.mock_service_account.get.assert_called_with(
            'api/workspaces/my-seqr-billing/anvil-1kg project n\u00e5me with uni\u00e7\u00f8de/acl')
        self.assertEqual(self.mock_service_account.get.call_count, 4)

    def test_empty_project_page_data(self):
        super(MixProjectAPITest, self).test_empty_project_page_data()
        self.mock_list_workspaces.assert_not_called()
        self.mock_service_account.get.assert_not_called()
