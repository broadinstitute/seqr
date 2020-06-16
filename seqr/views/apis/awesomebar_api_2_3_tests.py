from __future__ import unicode_literals

from django.urls.base import reverse
from seqr.views.apis.awesomebar_api import awesomebar_autocomplete_handler
from seqr.views.utils.test_utils import AuthenticationTestCase


class AwesomebarAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    def test_awesomebar_autocomplete_handler(self):
        url = reverse(awesomebar_autocomplete_handler)
        self.check_require_login(url)

        response = self.client.get(url+"?q=1")
        self.assertEqual(response.status_code, 200)
        # No objects returned as user has no access
        self.assertSetEqual(
            set(response.json()['matches'].keys()), {'genes'}
        )

        self.login_collaborator()
        response = self.client.get(url + "?q=1")
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(
            set(response.json()['matches'].keys()), {'projects', 'families', 'analysis_groups', 'individuals', 'genes'}
        )

        response = self.client.get(url + "?q=T&categories=project_groups,projects,hpo_terms,omim")
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json()['matches'].keys()), {'projects', 'project_groups', 'omim', 'hpo_terms'})
