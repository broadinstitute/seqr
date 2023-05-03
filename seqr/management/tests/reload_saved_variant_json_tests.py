#-*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase
from seqr.models import Family

PROJECT_NAME = '1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
FAMILY_ID = '1'


class ReloadSavedVariantJsonTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('logging.getLogger')
    @mock.patch('seqr.views.utils.variant_utils.get_variants_for_variant_ids')
    def test_with_param_command(self, mock_get_variants, mock_get_logger):
        mock_get_variants.side_effect = lambda families, variant_ids, **kwargs: \
            [{'variantId': variant_id, 'familyGuids': [family.guid for family in families]}
             for variant_id in variant_ids]
        mock_logger = mock_get_logger.return_value

        # Test with a specific project and a family id.
        call_command('reload_saved_variant_json',
                     PROJECT_NAME,
                     '--family-id={}'.format(FAMILY_ID))

        family_1 = Family.objects.get(id=1)
        mock_get_variants.assert_called_with(
            [family_1], ['1-1562437-G-C', '1-46859832-G-A','21-3343353-GAGA-G'], user=None)

        logger_info_calls = [
            mock.call('Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Updated 3 variants for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call('  1kg project n\xe5me with uni\xe7\xf8de: Updated 3 variants')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)
        mock_get_variants.reset_mock()
        mock_logger.reset_mock()

        # Test for all projects and no specific family ids
        call_command('reload_saved_variant_json')

        self.assertEqual(mock_get_variants.call_count, 3)
        family_2 = Family.objects.get(id=2)
        mock_get_variants.assert_has_calls([
            mock.call(
                [family_1, family_2], ['1-1562437-G-C', '1-46859832-G-A', '12-48367227-TC-T', '21-3343353-GAGA-G'], user=None,
            ),
            mock.call([Family.objects.get(id=12)], ['12-48367227-TC-T', 'prefix_19107_DEL'], user=None),
            mock.call([Family.objects.get(id=14)], ['12-48367227-TC-T'], user=None)
        ], any_order=True)

        logger_info_calls = [
            mock.call('Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Updated 4 variants for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Project: Empty Project'),
            mock.call('Updated 0 variants for project Empty Project'),
            mock.call('Project: Test Reprocessed Project'),
            mock.call('Updated 2 variants for project Test Reprocessed Project'),
            mock.call('Project: Non-Analyst Project'),
            mock.call('Updated 1 variants for project Non-Analyst Project'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call('  1kg project n\xe5me with uni\xe7\xf8de: Updated 4 variants'),
            mock.call('  Test Reprocessed Project: Updated 2 variants'),
            mock.call('  Non-Analyst Project: Updated 1 variants'),
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)
        mock_get_variants.reset_mock()
        mock_logger.reset_mock()

        # Test with an exception.
        mock_get_variants.side_effect = Exception("Database error.")
        call_command('reload_saved_variant_json',
                     PROJECT_GUID,
                     '--family-id={}'.format(FAMILY_ID))

        mock_get_variants.assert_called_with([family_1], ['1-1562437-G-C', '1-46859832-G-A', '21-3343353-GAGA-G'], user=None)

        logger_info_calls = [
            mock.call('Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call('1 failed projects'),
            mock.call('  1kg project n\xe5me with uni\xe7\xf8de: Database error.')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)

        mock_logger.error.assert_called_with('Error in project 1kg project n\xe5me with uni\xe7\xf8de: Database error.')
