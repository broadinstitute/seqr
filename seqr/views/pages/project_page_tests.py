from django.test import TestCase
from django.urls.base import reverse
from seqr.views.pages.project_page import project_page, project_page_data #, export_project_families
from seqr.views.utils.test_utils import _check_login


class ProjectPageTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_project_page(self):
        url = reverse(project_page, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_project_page_data(self):
        url = reverse(project_page_data, args=['R0001_1kg'])
        _check_login(self, url)

        #response = self.client.get(url)
        #self.assertEqual(response.status_code, 200)


    #def test_export_projects_table(self):
        #url = reverse(export_project_families)

        #_check_login(self, url)

        #response = self.client.get(url+"?file_format=tsv")
        #self.assertEqual(response.status_code, 200)

        #response = self.client.get(url+"?file_format=xls")
        #self.assertEqual(response.status_code, 200)

        #self.assertRaisesRegexp(ValueError, "file_format", lambda:
        #    self.client.get(reverse(export_projects_table)+"?file_format=xyz")
        #)


