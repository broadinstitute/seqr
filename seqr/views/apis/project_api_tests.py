import json
import mock
from datetime import datetime
from django.test import TestCase
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.project_api import create_project_handler, delete_project_handler, update_project_handler, \
    project_page_data, export_project_individuals_handler
from seqr.views.utils.test_utils import _check_login, create_proxy_request_stub


MME_INDIVIDUAL_ID = 'IND_012'

PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'
FAMILY_GUID = 'F000001_1'
ANALYSIS_GROUP_GUID = 'AG0000183_test_group'


def find_mme_matches(search):
    return [{
        'insertion_date': '2018-07-01',
        'project_id': search['project_id'],
        'family_id': search.get('family_id'),
        'seqr_id': MME_INDIVIDUAL_ID,
        'submitted_data': {},
    }]


def get_objects_for_group(can_view_group, permission, object_cls):
    return object_cls.objects.all()


class ProjectAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    @mock.patch('seqr.views.utils.phenotips_utils.proxy_request', create_proxy_request_stub(201))
    def test_create_update_and_delete_project(self):
        create_project_url = reverse(create_project_handler)
        _check_login(self, create_project_url)

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

    @mock.patch('seqr.views.utils.orm_to_json_utils.get_objects_for_group', get_objects_for_group)
    def test_project_page_data(self):
        url = reverse(project_page_data, args=[PROJECT_GUID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid', 'locusListsByGuid',
             'analysisGroupsByGuid', 'genesById'}
        )
        self.assertSetEqual(
            set(response_json['projectsByGuid'][PROJECT_GUID]['variantTagTypes'][0].keys()),
            {'variantTagTypeGuid', 'name', 'category', 'description', 'color', 'order', 'numTags', 'numTagsPerFamily'}
        )
        self.assertSetEqual(
            set(response_json['projectsByGuid'][PROJECT_GUID].keys()),
            {'collaborators', 'locusListGuids', 'variantTagTypes', 'variantFunctionalTagTypes',
             'detailsLoaded', 'projectGuid', 'projectCategoryGuids', 'canEdit', 'name', 'description', 'createdDate',
             'lastModifiedDate', 'isPhenotipsEnabled', 'phenotipsUserId', 'deprecatedProjectId', 'hasNewSearch',
             'lastAccessedDate', 'isMmeEnabled', 'mmePrimaryDataOwner', 'mmeContactInstitution', 'mmeContactUrl',
             'genomeVersion', 'discoveryTags'}
        )
        self.assertEqual(
            response_json['projectsByGuid'][PROJECT_GUID]['lastAccessedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )
        discovery_tags = response_json['projectsByGuid'][PROJECT_GUID]['discoveryTags']
        self.assertEqual(len(discovery_tags), 1)
        self.assertEqual(discovery_tags[0]['variantGuid'], 'SV0000001_2103343353_r0390_100')
        self.assertListEqual(response_json['genesById'].keys(), ['ENSG00000135953'])
        self.assertSetEqual(
            set(response_json['familiesByGuid'].values()[0].keys()),
            {'projectGuid', 'familyGuid', 'individualGuids', 'analysedBy', 'pedigreeImage', 'familyId', 'displayName',
             'description', 'analysisNotes', 'analysisSummary', 'causalInheritanceMode', 'analysisStatus',
             'pedigreeImage', 'internalAnalysisStatus', 'internalCaseReviewNotes', 'internalCaseReviewSummary',
             'createdDate', 'codedPhenotype', 'postDiscoveryOmimNumber', 'pubmedIds', 'assignedAnalyst',
             'successStoryTypes', 'successStory'}
        )
        self.assertSetEqual(
            set(response_json['individualsByGuid'].values()[0].keys()),
            {'projectGuid', 'familyGuid', 'individualGuid', 'sampleGuids', 'caseReviewStatusLastModifiedBy',
             'phenotipsData', 'individualId', 'paternalId', 'maternalId', 'sex', 'affected', 'displayName', 'notes',
             'phenotipsPatientId', 'phenotipsData', 'createdDate', 'lastModifiedDate', 'caseReviewStatus',
             'caseReviewDiscussion', 'caseReviewStatusLastModifiedDate', 'caseReviewStatusLastModifiedBy',
             'paternalGuid', 'maternalGuid', 'mmeSubmittedDate', 'mmeDeletedDate', 'popPlatformFilters', 'filterFlags',
             'population'}
        )
        self.assertSetEqual(
            set(response_json['samplesByGuid'].values()[0].keys()),
            {'projectGuid', 'individualGuid', 'sampleGuid', 'createdDate', 'sampleType', 'datasetType', 'sampleId',
             'isActive', 'loadedDate', 'datasetFilePath', 'elasticsearchIndex'}
        )
        self.assertSetEqual(
            set(response_json['locusListsByGuid'].values()[0].keys()),
            {'locusListGuid', 'description', 'lastModifiedDate', 'numEntries', 'isPublic', 'createdBy', 'createdDate',
             'canEdit', 'name'}
        )
        self.assertSetEqual(
            set(response_json['analysisGroupsByGuid'].values()[0].keys()),
            {'analysisGroupGuid', 'description', 'name', 'projectGuid', 'familyGuids'}
        )

    @mock.patch('seqr.views.utils.orm_to_json_utils.get_objects_for_group', get_objects_for_group)
    def test_empty_project_page_data(self):
        url = reverse(project_page_data, args=[EMPTY_PROJECT_GUID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid', 'locusListsByGuid',
             'analysisGroupsByGuid', 'genesById'}
        )
        self.assertListEqual(response_json['projectsByGuid'].keys(), [EMPTY_PROJECT_GUID])
        self.assertDictEqual(response_json['familiesByGuid'], {})
        self.assertDictEqual(response_json['individualsByGuid'], {})
        self.assertDictEqual(response_json['samplesByGuid'], {})
        self.assertDictEqual(response_json['analysisGroupsByGuid'], {})
        self.assertDictEqual(response_json['genesById'], {})

    def test_export_tables(self):
        url = reverse(export_project_individuals_handler, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url + "?file_format=tsv")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url + "?file_format=xls")
        self.assertEqual(response.status_code, 200)
