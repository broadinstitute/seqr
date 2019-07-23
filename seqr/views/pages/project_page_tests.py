import mock
from datetime import datetime
from django.test import TestCase
from django.urls.base import reverse

from seqr.views.pages.project_page import project_page_data, export_project_individuals_handler
from seqr.views.utils.test_utils import _check_login

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


class ProjectPageTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.apis.locus_list_api.get_objects_for_group', get_objects_for_group)
    def test_project_page_data(self):
        url = reverse(project_page_data, args=[PROJECT_GUID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid'}
        )
        self.assertSetEqual(
            set(response_json['projectsByGuid'][PROJECT_GUID]['variantTagTypes'][0].keys()),
            {'variantTagTypeGuid', 'name', 'category', 'description', 'color', 'order', 'is_built_in', 'numTags',
             'numTagsPerFamily'}
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
            response_json['projectsByGuid'][PROJECT_GUID]['lastAccessedDate'][:10], datetime.today().strftime('%Y-%m-%d')
        )
        self.assertSetEqual(
            set(response_json['familiesByGuid'].values()[0].keys()),
            {'projectGuid', 'familyGuid', 'individualGuids', 'analysedBy', 'pedigreeImage', 'familyId', 'displayName',
             'description', 'analysisNotes', 'analysisSummary', 'causalInheritanceMode', 'analysisStatus',
             'pedigreeImage', 'internalAnalysisStatus', 'internalCaseReviewNotes', 'internalCaseReviewSummary',
             'createdDate', 'codedPhenotype', 'postDiscoveryOmimNumber', 'pubmedIds', 'assignedAnalyst'}
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
             'sampleStatus',  'loadedDate', 'datasetFilePath', 'elasticsearchIndex'}
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

    @mock.patch('seqr.views.apis.locus_list_api.get_objects_for_group', get_objects_for_group)
    def test_empty_project_page_data(self):
        url = reverse(project_page_data, args=[EMPTY_PROJECT_GUID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid'}
        )
        self.assertListEqual(response_json['projectsByGuid'].keys(), [EMPTY_PROJECT_GUID])
        self.assertDictEqual(response_json['familiesByGuid'], {})
        self.assertDictEqual(response_json['individualsByGuid'], {})
        self.assertDictEqual(response_json['samplesByGuid'], {})
        self.assertDictEqual(response_json['analysisGroupsByGuid'], {})

    def test_export_tables(self):
        url = reverse(export_project_individuals_handler, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url+"?file_format=tsv")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url+"?file_format=xls")
        self.assertEqual(response.status_code, 200)
