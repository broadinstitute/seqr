from __future__ import unicode_literals

import json
from django.urls.base import reverse
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.utils.test_utils import AuthenticationTestCase

from seqr.models import Project

PROJECT_GUID = 'R0001_1kg'
PROJECT_CAT_GUID2 = 'PC000002_categry_with_unicde'
PROJECT_CAT_GUID3 = 'PC000003_test_category_name'
NEW_PROJECT_CAT_NAME = 'New project category'


class ProjectCategoriesAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    def test_project_categories_api(self):
        url = reverse(update_project_categories_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

        category_guids = [PROJECT_CAT_GUID2, NEW_PROJECT_CAT_NAME]
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'categories': category_guids
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'projectsByGuid', 'projectCategoriesByGuid'})
        self.assertListEqual(list(response_json['projectsByGuid'].keys()), [PROJECT_GUID])
        updated_guid_set = set(response_json['projectCategoriesByGuid'].keys())

        project = Project.objects.get(guid=PROJECT_GUID)

        project_categories = [ project_category for project_category in project.projectcategory_set.all()]
        self.assertEqual(project_categories[0].guid, PROJECT_CAT_GUID2)
        self.assertNotIn(project_categories[0].guid, updated_guid_set)
        self.assertEqual(project_categories[1].name, NEW_PROJECT_CAT_NAME)
        self.assertIn(project_categories[1].guid, updated_guid_set)
        new_guid = project_categories[1].guid

        self.assertEqual(len(response_json['projectsByGuid'][PROJECT_GUID]['projectCategoryGuids']), 2)
        self.assertListEqual([PROJECT_CAT_GUID2, new_guid], response_json['projectsByGuid'][PROJECT_GUID]['projectCategoryGuids'])

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'categories': []
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'projectsByGuid', 'projectCategoriesByGuid'})
        self.assertListEqual(list(response_json['projectsByGuid'].keys()), [PROJECT_GUID])

        self.assertEqual(len(response_json['projectsByGuid'][PROJECT_GUID]['projectCategoryGuids']), 0)

        project = Project.objects.get(guid=PROJECT_GUID)
        project_category_guids_in_db = [project_category.guid for project_category in project.projectcategory_set.all()]
        self.assertListEqual(project_category_guids_in_db, [])
        self.assertIsNone(response_json['projectCategoriesByGuid'][PROJECT_CAT_GUID2])
        self.assertIsNone(response_json['projectCategoriesByGuid'][new_guid])
