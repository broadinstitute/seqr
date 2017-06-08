import mock
from django.test import TestCase
from django.urls.base import reverse

from seqr.views.pages.dashboard_page import export_projects_table
from seqr.views.pages.project_page import project_page, project_page_data, \
    export_project_families, export_project_individuals
from seqr.views.utils.test_utils import _check_login


def _has_gene_search(project):
    return True


class ProjectPageTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.pages.project_page._has_gene_search', _has_gene_search)
    def test_project_page(self):
        url = reverse(project_page, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.pages.project_page._has_gene_search', _has_gene_search)
    def test_project_page_data(self):
        url = reverse(project_page_data, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.pages.project_page._has_gene_search', _has_gene_search)
    def test_export_tables(self):
        for i, export_func in enumerate([export_project_families, export_project_individuals]):
            url = reverse(export_func, args=['R0001_1kg'])
            if i == 0:
                _check_login(self, url)

            response = self.client.get(url+"?file_format=tsv")
            self.assertEqual(response.status_code, 200)

            response = self.client.get(url+"?file_format=xls")
            self.assertEqual(response.status_code, 200)
