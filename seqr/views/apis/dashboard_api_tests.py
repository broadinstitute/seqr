from django.urls.base import reverse
from seqr.views.apis.dashboard_api import dashboard_page_data, export_projects_table_handler
from seqr.views.utils.test_utils import AuthenticationTestCase


class DashboardPageTest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    def test_dashboard_page_data(self):
        url = reverse(dashboard_page_data)
        self.check_collaborator_login(url)

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
             'isMmeEnabled', 'lastAccessedDate', 'lastModifiedDate', 'projectCategoryGuids', 'projectGuid',
             'mmePrimaryDataOwner', 'mmeContactInstitution', 'mmeContactUrl', 'name', 'numFamilies', 'numIndividuals',
             'numVariantTags', }
        )

    def test_export_projects_table(self):
        url = reverse(export_projects_table_handler)

        self.check_collaborator_login(url)

        response = self.client.get(url+"?file_format=tsv")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url+"?file_format=xls")
        self.assertEqual(response.status_code, 200)

