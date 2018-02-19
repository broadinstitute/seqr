import json
from django.test import TestCase
from django.urls.base import reverse
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.utils.test_utils import _check_login


class ProjectCategoriesAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_project_categories_api(self):
        url = reverse(update_project_categories_handler, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'form': {
                'categories': []
            }
        }))
        self.assertEqual(response.status_code, 200)
