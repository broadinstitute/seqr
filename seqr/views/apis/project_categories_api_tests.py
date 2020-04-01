import json
from django.test import TestCase
from django.urls.base import reverse
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.utils.test_utils import _check_login

from seqr.models import Project, ProjectCategory

PROJECT_GUID = 'R0001_1kg'
PROJECT_CAT_GUID2 = 'PC000002_categry_with_unicde'
PROJECT_CAT_GUID3 = 'PC000003_test_category_name'
NEW_PROJECT_CAT_NAME = 'New project category'


class ProjectCategoriesAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_project_categories_api(self):
        url = reverse(update_project_categories_handler, args=[PROJECT_GUID])
        _check_login(self, url)

        category_guids = [PROJECT_CAT_GUID2, NEW_PROJECT_CAT_NAME]
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'categories': category_guids
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['projectsByGuid', 'projectCategoriesByGuid'])
        self.assertListEqual(response_json['projectsByGuid'].keys(), [PROJECT_GUID])
        updated_guid_set = set(response_json['projectCategoriesByGuid'].keys())

        project = Project.objects.get(guid=PROJECT_GUID)
        project_category_guids_in_db = set()
        # Exam all the project_category guids from the db against the updated guids.
        for project_category in project.projectcategory_set.all():
            if project_category.guid == PROJECT_CAT_GUID2:
                # The old guid must not be updated
                self.assertNotIn(project_category.guid, updated_guid_set)
            else:
                # The new project category must have as name as given one
                self.assertEqual(project_category.name, NEW_PROJECT_CAT_NAME)
                self.assertIn(project_category.guid, updated_guid_set)
            project_category_guids_in_db.add(project_category.guid)
        for updated_guid in updated_guid_set:
            if updated_guid not in project_category_guids_in_db:
                # The updated project category which doesn't exist in the db must have a None value
                self.assertIsNone(response_json['projectCategoriesByGuid'][updated_guid])

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'categories': []
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['projectsByGuid', 'projectCategoriesByGuid'])
        self.assertListEqual(response_json['projectsByGuid'].keys(), [PROJECT_GUID])

        project = Project.objects.get(guid=PROJECT_GUID)
        project_category_guids_in_db = set()
        for project_category in project.projectcategory_set.all():
            project_category_guids_in_db.add(project_category.guid)
        self.assertSetEqual(project_category_guids_in_db, set([]))
        for project_category_guid in response_json['projectCategoriesByGuid'].keys():
            self.assertIsNone(response_json['projectCategoriesByGuid'][project_category_guid])
