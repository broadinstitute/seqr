# -*- coding: utf-8 -*-

import json

from django.test import TestCase

from openpyxl import load_workbook
from StringIO import StringIO

from seqr.models import Individual
from seqr.views.apis.individual_api import export_individuals, _parse_phenotips_data


class ExportTableUtilsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_export_individuals(self):
        test_individuals = Individual.objects.filter(individual_id='NA19675')

        # test tsv with all columns
        response = export_individuals(
            'test_individuals_table',
            test_individuals,
            'tsv',
            include_project_column=True,
            include_case_review_columns=True,
            include_phenotips_columns=True,
        )
        self.assertEqual(response.status_code, 200)
        rows = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]
        HEADER = [
            'project', 'family_id', 'individual_id', 'paternal_id', 'maternal_id', 'sex', 'affected_status', 'notes',
            'case_review_status', 'case_review_status_last_modified_date', 'case_review_status_last_modified_by', 'case_review_discussion',
            'phenotips_features_present', 'phenotips_features_absent', 'paternal_ancestry', 'maternal_ancestry', 'age_of_onset'
        ]

        self.assertListEqual(rows[0], HEADER)
        self.assertEqual(len(rows), 2)

        # test Excel format
        response = export_individuals('test_families_table', test_individuals, 'xls', include_project_column=True, include_case_review_columns=True, include_phenotips_columns=True)
        self.assertEqual(response.status_code, 200)
        wb = load_workbook(StringIO(response.content))
        worksheet = wb.active

        # test unknown format
        self.assertRaisesRegexp(ValueError, '.*format.*',
                                lambda: export_individuals('test_families_table', test_individuals, file_format='unknown_format')
                                )

    def test_parse_phenotips_data(self):
        test_individuals = Individual.objects.filter(individual_id='NA19675')

        phenotips_json = json.loads(test_individuals[0].phenotips_data)

        parsed_data = _parse_phenotips_data(phenotips_json)

        self.assertSetEqual(
            set(parsed_data.keys()),
            {'age_of_onset', 'candidate_genes', 'maternal_ancestry', 'paternal_ancestry', 'phenotips_features_absent', 'phenotips_features_present', 'previously_tested_genes'}
        )

        self.assertEqual(parsed_data['age_of_onset'], 'Adult onset')
        self.assertEqual(parsed_data['candidate_genes'], 'EHBP1L1 (comments EHBP1L1), ACY3 (comments ACY3)')
        self.assertEqual(parsed_data['paternal_ancestry'], 'African Americans')
        self.assertEqual(parsed_data['maternal_ancestry'], 'Azerbaijanis')
        self.assertEqual(parsed_data['phenotips_features_absent'], 'Arrhythmia, Complete atrioventricular canal defect, Failure to thrive')
        self.assertEqual(parsed_data['phenotips_features_present'], 'Defect in the atrial septum, Morphological abnormality of the central nervous system, Tetralogy of Fallot')
        self.assertEqual(parsed_data['previously_tested_genes'], 'IKBKAP (comments IKBKAP), CCDC102B (comments for CCDC102B)')
