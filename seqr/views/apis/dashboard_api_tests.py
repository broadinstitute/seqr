from django.test import TestCase
from django.urls.base import reverse
from seqr.views.apis.dashboard_api import dashboard_page_data, export_projects_table_handler
from seqr.views.utils.test_utils import _check_login


class DashboardPageTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_dashboard_page_data(self):
        url = reverse(dashboard_page_data)
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'projectsByGuid', 'projectCategoriesByGuid'})
        self.assertSetEqual(
            set(response_json['projectCategoriesByGuid'].values()[0].keys()),
            {'created_by_id', 'created_date', 'guid', 'id', 'last_modified_date', 'name'}
        )
        self.assertSetEqual(
            set(response_json['projectsByGuid'].values()[0].keys()),
            {'analysisStatusCounts', 'canEdit', 'createdDate', 'description', 'genomeVersion', 'sampleTypeCounts',
             'isMmeEnabled', 'isPhenotipsEnabled', 'lastAccessedDate', 'lastModifiedDate', 'projectCategoryGuids',
             'mmePrimaryDataOwner', 'mmeContactInstitution', 'mmeContactUrl', 'name', 'numFamilies', 'numIndividuals',
             'numVariantTags', 'phenotipsUserId', 'projectGuid', }
        )

    def test_export_projects_table(self):
        url = reverse(export_projects_table_handler)

        _check_login(self, url)

        response = self.client.get(url+"?file_format=tsv")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url+"?file_format=xls")
        self.assertEqual(response.status_code, 200)

        #self.assertRaisesRegexp(ValueError, "file_format", lambda:
        #    self.client.get(reverse(export_projects_table)+"?file_format=xyz")
        #)


