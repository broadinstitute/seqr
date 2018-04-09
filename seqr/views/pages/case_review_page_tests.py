from django.test import TestCase
from django.urls.base import reverse
from seqr.views.pages.case_review_page import export_case_review_families_handler, export_case_review_individuals_handler
from seqr.views.utils.test_utils import _check_login


class DashboardPageTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_export_case_review_families(self):
        url = reverse(export_case_review_families_handler, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url+"?file_format=tsv")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url+"?file_format=xls")
        self.assertEqual(response.status_code, 200)

    def test_export_case_review_individuals(self):
        url = reverse(export_case_review_individuals_handler, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url+"?file_format=tsv")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url+"?file_format=xls")
        self.assertEqual(response.status_code, 200)



