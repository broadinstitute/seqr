# -*- coding: utf-8 -*-
from __future__ import  unicode_literals
from builtins import str

import mock

from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError
from seqr.utils.elasticsearch.es_utils_2_3_tests import PARSED_VARIANTS
from seqr.models import SavedVariant

SAVED_VARIANT_GUID = 'SV0000001_2103343353_r0390_100'
VARIANT_ID = '21-3343353-GAGA-G'


class LiftVariantToHg38Test(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.lift_variant_to_hg38.input')
    @mock.patch('seqr.management.commands.lift_variant_to_hg38.logger')
    @mock.patch('seqr.management.commands.lift_variant_to_hg38.get_single_es_variant')
    def test_command(self, mock_single_es_variants, mock_logger, mock_input):
        # Test user did not confirm.
        mock_input.return_value = 'n'
        with self.assertRaises(CommandError) as ce:
            call_command('lift_variant_to_hg38', SAVED_VARIANT_GUID, VARIANT_ID)

        self.assertEqual(str(ce.exception), 'Error: user did not confirm')

        # Test user did confirm.
        mock_single_es_variants.return_value = PARSED_VARIANTS[0]
        mock_input.return_value = 'y'
        call_command('lift_variant_to_hg38', SAVED_VARIANT_GUID, VARIANT_ID)
        mock_logger.info.assert_called_with('---Done---')

        saved_variant = SavedVariant.objects.get(guid = SAVED_VARIANT_GUID)
        mock_single_es_variants.assert_called_with([saved_variant.family], VARIANT_ID,
                                                   return_all_queried_families = True)

        self.assertListEqual(
            [PARSED_VARIANTS[0]['xpos'], PARSED_VARIANTS[0]['ref'], PARSED_VARIANTS[0]['alt'], PARSED_VARIANTS[0]],
            [saved_variant.xpos_start, saved_variant.ref, saved_variant.alt, saved_variant.saved_variant_json])
