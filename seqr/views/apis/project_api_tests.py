import json
from django.test import TestCase
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.project_api import create_project, update_project, delete_project
from seqr.views.utils.test_utils import _check_login


class ProjectAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_project_api(self):
        url = reverse(create_project)
        _check_login(self, url)

        # check validation of bad requests
        response = self.client.post(url, content_type='application/json', data=json.dumps({'bad_json': None}))
        self.assertEqual(response.status_code, 400)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'form': {'missing_name': True}}))
        self.assertEqual(response.status_code, 400)

        # send valid request to create project
        response = self.client.post(url, content_type='application/json', data=json.dumps(
            {'form': {'name': 'new_project', 'description': 'new project description'}}
        ))

        self.assertEqual(response.status_code, 200)

        # check that project was created
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 1)
        self.assertEqual(new_project[0].description, 'new project description')
