from django.test import TestCase
from django.urls.base import reverse
from seqr.views.apis.awesomebar_api import awesomebar_autocomplete_handler
from seqr.views.utils.test_utils import _check_login


class AwesomebarAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    def test_awesomebar_autocomplete_handler(self):
        url = reverse(awesomebar_autocomplete_handler)
        _check_login(self, url)

        response = self.client.get(url+"?q=1")
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(
            set(response.json()['matches'].keys()), {'projects', 'families', 'analysis_groups', 'individuals', 'genes'}
        )

        response = self.client.get(url + "?q=T&categories=project_groups,projects")
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json()['matches'].keys()), {'projects', 'project_groups'})
