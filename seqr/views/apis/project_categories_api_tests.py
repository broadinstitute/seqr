import json
from django.test import TestCase
from django.urls.base import reverse
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.utils.test_utils import _check_login

PROJECT_GUID = 'R0001_1kg'


class ProjectCategoriesAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_project_categories_api(self):
        url = reverse(update_project_categories_handler, args=[PROJECT_GUID])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'categories': ['PC000002_categry_with_unicde', 'PC000003_categry_with_unicde']
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['projectsByGuid', 'projectCategoriesByGuid'])
        self.assertListEqual(response_json['projectsByGuid'].keys(), [PROJECT_GUID])

