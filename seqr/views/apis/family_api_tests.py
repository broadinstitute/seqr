# -*- coding: utf-8 -*-

import json

from django.test import TestCase

from openpyxl import load_workbook
from StringIO import StringIO

from seqr.models import Family
from seqr.views.apis.family_api import export_families


class ExportTableUtilsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_export_families(self):
        test_families = Family.objects.all()

        # test tsv with all columns
        response = export_families('test_families_table', test_families, 'tsv', include_project_column=True, include_case_review_columns=True)
        self.assertEqual(response.status_code, 200)
        rows = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]
        HEADER = ['project', 'family_id', 'display_name', 'created_date', 'description', 'analysis_status',  'analysis_summary', 'analysis_notes', 'internal_case_review_summary', 'internal_case_review_notes']
        self.assertListEqual(rows[0], HEADER)
        self.assertEqual(len(rows), 13)

        # test tsv without project column
        response = export_families('test_families_table', test_families, 'tsv', include_project_column=False, include_case_review_columns=True)
        self.assertEqual(response.status_code, 200)
        rows = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]
        HEADER = ['family_id', 'display_name', 'created_date', 'description', 'analysis_status', 'analysis_summary', 'analysis_notes', 'internal_case_review_summary', 'internal_case_review_notes']
        self.assertListEqual(rows[0], HEADER)
        self.assertEqual(len(rows), 13)

        # test tsv without case review columns
        response = export_families('test_families_table', test_families, 'tsv', include_project_column=False, include_case_review_columns=False)
        self.assertEqual(response.status_code, 200)
        rows = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]
        HEADER = ['family_id', 'display_name', 'created_date', 'description', 'analysis_status', 'analysis_summary', 'analysis_notes']
        self.assertListEqual(rows[0], HEADER)
        self.assertEqual(len(rows), 13)

        # test Excel format
        response = export_families('test_families_table', test_families, 'xls', include_project_column=True, include_case_review_columns=True)
        self.assertEqual(response.status_code, 200)
        wb = load_workbook(StringIO(response.content))
        worksheet = wb.active
        self.assertListEqual([cell.value for cell in worksheet['A']], ['Project'] + [u'1kg project nåme with uniçøde']*12)
        self.assertListEqual([cell.value for cell in worksheet['B']], ['Family Id', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'])
        self.assertListEqual([cell.value for cell in worksheet['C']], ['Display Name', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'])

        # test unknown format
        self.assertRaisesRegexp(ValueError, '.*format.*',
                                lambda: export_families('test_families_table', test_families, file_format='unknown_format')
                                )
