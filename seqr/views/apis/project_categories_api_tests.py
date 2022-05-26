import json
from django.urls.base import reverse
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.utils.test_utils import AuthenticationTestCase

from seqr.models import Project
from settings import ANALYST_PROJECT_CATEGORY

PROJECT_GUID = 'R0003_test'
ADDED_PROJECT_CAT_GUID = 'PC000002_categry_with_unicde'
EXISTING_PROJECT_CAT_GUID = 'PC000003_test_category_name'
NEW_PROJECT_CAT_NAME = 'New project category'


class ProjectCategoriesAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    def test_project_categories_api(self):
        url = reverse(update_project_categories_handler, args=[PROJECT_GUID])
        self.check_manager_login(url)

        category_guids = [EXISTING_PROJECT_CAT_GUID, ADDED_PROJECT_CAT_GUID, NEW_PROJECT_CAT_NAME]
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectCategoryGuids': category_guids
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'projectsByGuid', 'projectCategoriesByGuid'})
        self.assertListEqual(list(response_json['projectsByGuid'].keys()), [PROJECT_GUID])
        updated_guid_set = set(response_json['projectCategoriesByGuid'].keys())

        project = Project.objects.get(guid=PROJECT_GUID)

        project_categories = [project_category for project_category in
                              project.projectcategory_set.exclude(name=ANALYST_PROJECT_CATEGORY).order_by('guid')]
        self.assertEqual(project_categories[0].guid, ADDED_PROJECT_CAT_GUID)
        self.assertNotIn(project_categories[0].guid, updated_guid_set)
        self.assertEqual(project_categories[1].guid, EXISTING_PROJECT_CAT_GUID)
        self.assertNotIn(project_categories[1].guid, updated_guid_set)
        self.assertEqual(project_categories[2].name, NEW_PROJECT_CAT_NAME)
        self.assertIn(project_categories[2].guid, updated_guid_set)
        new_guid = project_categories[2].guid

        self.assertEqual(len(response_json['projectsByGuid'][PROJECT_GUID]['projectCategoryGuids']), 3)
        self.assertSetEqual(
            {EXISTING_PROJECT_CAT_GUID, ADDED_PROJECT_CAT_GUID, new_guid},
            set(response_json['projectsByGuid'][PROJECT_GUID]['projectCategoryGuids']))

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectCategoryGuids': []
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual(set(response_json.keys()), {'projectsByGuid', 'projectCategoriesByGuid'})
        self.assertListEqual(list(response_json['projectsByGuid'].keys()), [PROJECT_GUID])

        self.assertEqual(len(response_json['projectsByGuid'][PROJECT_GUID]['projectCategoryGuids']), 0)

        project = Project.objects.get(guid=PROJECT_GUID)
        project_category_guids_in_db = [
            project_category.guid for project_category in project.projectcategory_set.exclude(name=ANALYST_PROJECT_CATEGORY)]
        self.assertListEqual(project_category_guids_in_db, [])
        self.assertIsNone(response_json['projectCategoriesByGuid'][new_guid])
