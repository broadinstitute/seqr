import json
from django.test import TestCase
from django.urls.base import reverse
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.utils.test_utils import _check_login

PROJECT_GUID = 'R0001_1kg'
PROJECT_CAT_GUID2 = 'PC000002_categry_with_unicde'
PROJECT_CAT_GUID3 = 'PC000003_test_category_name'
PROJECT_CAT_GUID4 = 'PC000004_new_project_category'
PROJECT_CAT_GUID5 = 'PC000005_pc000002_categry_with'
NEW_PROJECT_CAT_NAME = 'New project category'


class ProjectCategoriesAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_project_categories_api(self):
        url = reverse(update_project_categories_handler, args=[PROJECT_GUID])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'categories': []
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['projectsByGuid', 'projectCategoriesByGuid'])
        self.assertListEqual(response_json['projectsByGuid'].keys(), [PROJECT_GUID])
        self.assertListEqual(response_json['projectCategoriesByGuid'].keys(), [PROJECT_CAT_GUID3, PROJECT_CAT_GUID2])

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'categories': ['PC000002_categry_with_unicde', NEW_PROJECT_CAT_NAME]
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['projectsByGuid', 'projectCategoriesByGuid'])
        self.assertListEqual(response_json['projectsByGuid'].keys(), [PROJECT_GUID])
        self.assertListEqual(response_json['projectCategoriesByGuid'].keys(), [PROJECT_CAT_GUID4, PROJECT_CAT_GUID5])
        self.assertEqual(response_json['projectCategoriesByGuid'][PROJECT_CAT_GUID4]['name'], NEW_PROJECT_CAT_NAME)
