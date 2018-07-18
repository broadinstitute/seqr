import json
import mock

from django.test import TestCase
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.project_api import create_project_handler, delete_project_handler
from seqr.views.utils.test_utils import _check_login, create_proxy_request_stub


class ProjectAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.apis.phenotips_api.proxy_request', create_proxy_request_stub(201))
    def test_create_update_and_delete_project(self):
        create_project_url = reverse(create_project_handler)
        _check_login(self, create_project_url)

        # check validation of bad requests
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps({'bad_json': None}))
        self.assertEqual(response.status_code, 400)

        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps({'form': {'missing_name': True}}))
        self.assertEqual(response.status_code, 400)

        # send valid request to create project
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps(
            {'name': 'new_project', 'description': 'new project description'}
        ))

        self.assertEqual(response.status_code, 200)

        # check that project was created
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 1)
        self.assertEqual(new_project[0].description, 'new project description')

        # delete the project
        delete_project_url = reverse(delete_project_handler, args=[new_project[0].guid])
        response = self.client.post(delete_project_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that project was deleted
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 0)
