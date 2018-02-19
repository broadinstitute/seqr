# -*- coding: utf-8 -*-

from django.test import TestCase

from openpyxl import load_workbook
from StringIO import StringIO

from seqr.views.utils.export_table_utils import export_table


class ExportTableUtilsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_export_table(self):
        header = ['column1', 'column2']
        rows = [['row1_v1', 'row1_v2'], ['row2_v1', 'row2_v2']]

        # test tsv format
        response = export_table('test_file', header, rows, file_format='tsv')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '\n'.join(['\t'.join(row) for row in [header]+rows]) + '\n')

        # test Excel format
        response = export_table('test_file', header, rows, file_format='xls')
        self.assertEqual(response.status_code, 200)
        wb = load_workbook(StringIO(response.content))
        worksheet = wb.active

        self.assertListEqual([cell.value for cell in worksheet['A']], ['Column1', 'row1_v1', 'row2_v1'])
        self.assertListEqual([cell.value for cell in worksheet['B']], ['Column2', 'row1_v2', 'row2_v2'])
        self.assertEqual([cell.value for cell in worksheet['C']], [None, None, None])

        # test unknown format
        self.assertRaisesRegexp(ValueError, '.*format.*',
            lambda: export_table('test_file', header, rows, file_format='unknown_format')
        )
