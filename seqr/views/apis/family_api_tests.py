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
        response = export_families('test_families_table', test_families, 'tsv', include_project_name=True, include_internal_case_review_summary=True, include_internal_case_review_notes=True)
        self.assertEqual(response.status_code, 200)
        rows = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]
        HEADER = ['Project', 'Family ID', 'Display Name', 'Created Date', 'Description', 'Analysis Status', 'Analysis Summary', 'Analysis Notes', 'Internal Case Review Summary', 'Internal Case Review Notes']
        self.assertListEqual(rows[0], HEADER)
        self.assertEqual(len(rows), 13)

        # test tsv without project column
        response = export_families('test_families_table', test_families, 'tsv', include_project_name=False, include_internal_case_review_summary=True, include_internal_case_review_notes=True)
        self.assertEqual(response.status_code, 200)
        rows = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]
        HEADER = ['Family ID', 'Display Name', 'Created Date', 'Description', 'Analysis Status', 'Analysis Summary', 'Analysis Notes', 'Internal Case Review Summary', 'Internal Case Review Notes']
        self.assertListEqual(rows[0], HEADER)
        self.assertEqual(len(rows), 13)

        # test tsv without case review columns
        response = export_families('test_families_table', test_families, 'tsv', include_project_name=False, include_internal_case_review_summary=False, include_internal_case_review_notes=False)
        self.assertEqual(response.status_code, 200)
        rows = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]
        HEADER = ['Family ID', 'Display Name', 'Created Date', 'Description', 'Analysis Status', 'Analysis Summary', 'Analysis Notes']
        self.assertListEqual(rows[0], HEADER)
        self.assertEqual(len(rows), 13)

        # test Excel format
        response = export_families('test_families_table', test_families, 'xls', include_project_name=True, include_internal_case_review_summary=True, include_internal_case_review_notes=True)
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
