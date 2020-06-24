# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.test import TestCase

from seqr.models import Family, Individual, Sample
from seqr.views.utils.pedigree_image_utils import _get_parsed_individuals


class PedigreeImageTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_get_parsed_individuals(self):

        test_family = Family.objects.get(guid='F000001_1')
        parsed_data = _get_parsed_individuals(test_family)
        self.assertDictEqual(parsed_data, {
            'NA19675_1': {
                'individualId': 'NA19675_1',
                'paternalId': 'NA19678',
                'maternalId': 'NA19679',
                'sex': '1',
                'affected': '2',
            },
            'NA19678': {
                'individualId': 'NA19678',
                'paternalId': '0',
                'maternalId': '0',
                'sex': '1',
                'affected': '1',
            },
            'NA19679': {
                'individualId': 'NA19679',
                'paternalId': '0',
                'maternalId': '0',
                'sex': '2',
                'affected': '1',
            }
        })

        # Create placeholder when only has one parent
        Sample.objects.get(guid='S000130_na19678').delete()
        Individual.objects.get(individual_id='NA19678').delete()
        parsed_data = _get_parsed_individuals(test_family)
        placeholders = {individual_id: record for individual_id, record in parsed_data.items() if
                        individual_id.startswith('placeholder_')}
        self.assertEqual(len(placeholders), 1)
        placeholder_id = next(iter(placeholders))
        self.assertDictEqual(parsed_data, {
            'NA19675_1': {
                'individualId': 'NA19675_1',
                'paternalId': placeholder_id,
                'maternalId': 'NA19679',
                'sex': '1',
                'affected': '2',
            },
            'NA19679': {
                'individualId': 'NA19679',
                'paternalId': '0',
                'maternalId': '0',
                'sex': '2',
                'affected': '1',
            },
            placeholder_id: {
                'individualId': placeholder_id,
                'paternalId': '0',
                'maternalId': '0',
                'sex': '1',
                'affected': '9',
            }
        })

        # Do not generate for families with one individual
        no_individual_family = Family.objects.get(guid='F000003_3')
        self.assertIsNone(_get_parsed_individuals(no_individual_family))
