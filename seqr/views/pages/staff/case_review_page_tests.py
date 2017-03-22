from django.contrib.auth.models import User
from django.test import TestCase
from django.urls.base import reverse
from seqr.views.pages.staff.case_review_page import case_review_page, case_review_page_data, export_case_review_families, export_case_review_individuals
from seqr.views.utils.test_utils import _check_login


class DashboardPageTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_case_review_page(self):
        url = reverse(case_review_page, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_case_review_page_data(self):
        url = reverse(case_review_page_data, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_export_case_review_families(self):
        url = reverse(export_case_review_families, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url+"?file_format=tsv")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url+"?file_format=xls")
        self.assertEqual(response.status_code, 200)

    def test_export_case_review_individuals(self):
        url = reverse(export_case_review_individuals, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url+"?file_format=tsv")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url+"?file_format=xls")
        self.assertEqual(response.status_code, 200)



