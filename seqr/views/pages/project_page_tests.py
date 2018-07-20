import mock
from django.test import TestCase
from django.urls.base import reverse

from seqr.views.pages.project_page import project_page_data, export_project_individuals_handler
from seqr.views.utils.test_utils import _check_login


def _has_gene_search(project):
    return True


def get_objects_for_group(can_view_group, permission, object_cls):
    return object_cls.objects.all()


class ProjectPageTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.pages.project_page._has_gene_search', _has_gene_search)
    @mock.patch('seqr.views.apis.locus_list_api.get_objects_for_group', get_objects_for_group)
    def test_project_page_data(self):
        url = reverse(project_page_data, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'project', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid', 'locusListsByGuid'}
        )
        self.assertSetEqual(
            set(response_json['project'].keys()),
            {'collaborators', 'locusListGuids', 'variantTagTypes', 'variantFunctionalTagTypes', 'hasGeneSearch',
             'detailsLoaded', 'projectGuid', 'projectCategoryGuids', 'canEdit', 'name', 'description', 'createdDate',
             'lastModifiedDate', 'isPhenotipsEnabled', 'phenotipsUserId', 'deprecatedProjectId',
             'deprecatedLastAccessedDate', 'isMmeEnabled', 'mmePrimaryDataOwner', 'genomeVersion', 'discoveryTags'}
        )
        self.assertSetEqual(
            set(response_json['familiesByGuid'].values()[0].keys()),
            {'projectGuid', 'familyGuid', 'individualGuids', 'analysedBy', 'pedigreeImage', 'familyId', 'displayName',
             'description', 'analysisNotes', 'analysisSummary', 'causalInheritanceMode', 'analysisStatus',
             'pedigreeImage', 'internalAnalysisStatus', 'internalCaseReviewNotes', 'internalCaseReviewSummary',
             'createdDate'}
        )
        self.assertSetEqual(
            set(response_json['individualsByGuid'].values()[0].keys()),
            {'projectGuid', 'familyGuid', 'individualGuid', 'sampleGuids', 'caseReviewStatusLastModifiedBy',
             'phenotipsData', 'individualId', 'paternalId', 'maternalId', 'sex', 'affected', 'displayName', 'notes',
             'phenotipsPatientId', 'phenotipsData', 'createdDate', 'lastModifiedDate', 'caseReviewStatus',
             'caseReviewDiscussion', 'caseReviewStatusLastModifiedDate', 'caseReviewStatusLastModifiedBy'}
        )
        self.assertSetEqual(
            set(response_json['samplesByGuid'].values()[0].keys()),
            {'projectGuid', 'individualGuid', 'sampleGuid', 'createdDate', 'sampleType', 'datasetType', 'sampleId',
             'sampleStatus',  'loadedDate', 'datasetFilePath', 'elasticsearchIndex', 'datasetName'}
        )
        self.assertSetEqual(
            set(response_json['locusListsByGuid'].values()[0].keys()),
            {'locusListGuid', 'description', 'lastModifiedDate', 'numEntries', 'isPublic', 'createdBy', 'createdDate',
             'canEdit', 'name'}
        )

    @mock.patch('seqr.views.pages.project_page._has_gene_search', _has_gene_search)
    def test_export_tables(self):
        url = reverse(export_project_individuals_handler, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url+"?file_format=tsv")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url+"?file_format=xls")
        self.assertEqual(response.status_code, 200)
