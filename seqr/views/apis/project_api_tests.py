import json
import mock

from django.test import TestCase
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.project_api import create_project, update_project, delete_project
from seqr.views.utils.test_utils import _check_login, create_send_requests_to_phenotips_stub


class ProjectAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.apis.phenotips_api._send_request_to_phenotips', create_send_requests_to_phenotips_stub(201))
    def test_create_update_and_delete_project(self):
        create_project_url = reverse(create_project)
        _check_login(self, create_project_url)

        # check validation of bad requests
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps({'bad_json': None}))
        self.assertEqual(response.status_code, 400)

        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps({'form': {'missing_name': True}}))
        self.assertEqual(response.status_code, 400)

        # send valid request to create project
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps(
            {'form': {'name': 'new_project', 'description': 'new project description'}}
        ))

        self.assertEqual(response.status_code, 200)

        # check that project was created
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 1)
        self.assertEqual(new_project[0].description, 'new project description')

        # delete the project
        delete_project_url = reverse(delete_project, args=[new_project[0].guid])
        response = self.client.post(delete_project_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that project was deleted
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 0)
