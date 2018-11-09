# -*- coding: utf-8 -*-

import json
import mock

from django.test import TestCase
from django.urls.base import reverse

from openpyxl import load_workbook
from StringIO import StringIO

from seqr.models import Individual
from seqr.views.apis.individual_api import export_individuals, _parse_phenotips_data, edit_individuals_handler
from seqr.views.utils.test_utils import _check_login

PROJECT_GUID = 'R0001_1kg'

ID_UPDATE_GUID = "I000002_na19678"
UPDATED_ID = "NA19678_1"
UPDATED_MATERNAL_ID = "NA20870"

INDIVIDUAL_IDS_UPDATE_DATA = {
    "individualGuid": ID_UPDATE_GUID,
    "familyId": "1",
    "individualId": UPDATED_ID,
    "maternalId": UPDATED_MATERNAL_ID,
    "paternalId": "",
}

FAMILY_UPDATE_GUID = "I000007_na20870"
INDIVIDUAL_FAMILY_UPDATE_DATA = {
    "individualGuid": FAMILY_UPDATE_GUID,
    "familyId": "1",
    "individualId": UPDATED_MATERNAL_ID,
}

CHILD_UPDATE_GUID = "I000001_na19675"


class ProjectAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.utils.model_sync_utils.find_matching_xbrowse_model')
    def test_edit_individuals(self, mock_find_xbrowse_model):
        mock_find_xbrowse_model.return_value.has_elasticsearch_index.return_value = False

        edit_individuals_url = reverse(edit_individuals_handler, args=[PROJECT_GUID])
        _check_login(self, edit_individuals_url)

        # send invalid requests
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ["NA20870 is the mother of NA19678_1 but doesn't have a separate record in the table"])

        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA, INDIVIDUAL_FAMILY_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Editing individual_id is disabled for projects which still use the mongo datastore'])

        # send valid request
        mock_find_xbrowse_model.return_value.has_elasticsearch_index.return_value = True
        response = self.client.post(edit_individuals_url, content_type='application/json', data=json.dumps({
            'individuals': [INDIVIDUAL_IDS_UPDATE_DATA, INDIVIDUAL_FAMILY_UPDATE_DATA]
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertSetEqual({'F000001_1', 'F000003_3'}, set(response_json['familiesByGuid']))
        self.assertSetEqual({ID_UPDATE_GUID, FAMILY_UPDATE_GUID, CHILD_UPDATE_GUID, "I000003_na19679"},
                            set(response_json['familiesByGuid']['F000001_1']['individualGuids']))
        self.assertListEqual(response_json['familiesByGuid']['F000003_3']['individualGuids'], [])

        self.assertSetEqual({ID_UPDATE_GUID, FAMILY_UPDATE_GUID, CHILD_UPDATE_GUID}, set(response_json['individualsByGuid']))
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['individualId'], UPDATED_ID)
        self.assertEqual(response_json['individualsByGuid'][ID_UPDATE_GUID]['maternalId'], UPDATED_MATERNAL_ID)
        self.assertEqual(response_json['individualsByGuid'][CHILD_UPDATE_GUID]['paternalId'], UPDATED_ID)


class ExportTableUtilsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_export_individuals(self):
        test_individuals = Individual.objects.filter(individual_id='NA19675_1')

        # test tsv with all columns
        response = export_individuals(
            'test_individuals_table',
            test_individuals,
            'tsv',
            include_project_name=True,
            include_case_review_status=True,
            include_case_review_last_modified_date=True,
            include_case_review_last_modified_by=True,
            include_case_review_discussion=True,
            include_hpo_terms_present=True,
            include_hpo_terms_absent=True,
            include_paternal_ancestry=True,
            include_maternal_ancestry=True,
            include_age_of_onset=True,
        )
        self.assertEqual(response.status_code, 200)
        rows = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]

        self.assertEqual(rows[0][0], 'Project')
        self.assertEqual(rows[0][1], 'Family ID')
        self.assertEqual(len(rows), 2)

        # test Excel format
        response = export_individuals(
            'test_families_table',
            test_individuals,
            'xls',
            include_project_name=True,
            include_case_review_status=True,
            include_case_review_last_modified_date=True,
            include_case_review_last_modified_by=True,
            include_case_review_discussion=True,
            include_hpo_terms_present=True,
            include_hpo_terms_absent=True,
            include_paternal_ancestry=True,
            include_maternal_ancestry=True,
            include_age_of_onset=True)
        self.assertEqual(response.status_code, 200)
        wb = load_workbook(StringIO(response.content))
        worksheet = wb.active

        # test unknown format
        self.assertRaisesRegexp(ValueError, '.*format.*',
                                lambda: export_individuals('test_families_table', test_individuals, file_format='unknown_format'))

    def test_parse_phenotips_data(self):
        test_individuals = Individual.objects.filter(individual_id='NA19675_1')

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
