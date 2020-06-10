#-*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase
from seqr.models import Family

PROJECT_NAME = u'1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
FAMILY_ID = '1'


class ReloadSavedVariantJsonTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('logging.getLogger')
    @mock.patch('seqr.views.utils.variant_utils.get_es_variants_for_variant_ids')
    def test_with_param_command(self, mock_get_variants, mock_get_logger):
        mock_get_variants.side_effect = lambda families, variant_ids: \
            [{'variantId': variant_id, 'familyGuids': [family.guid for family in families]}
             for variant_id in variant_ids]
        mock_logger = mock_get_logger.return_value

        # Test with a specific project and a family id.
        call_command('reload_saved_variant_json',
                     PROJECT_NAME,
                     '--family-id={}'.format(FAMILY_ID))

        mock_get_variants.assert_called_with(
            set(Family.objects.filter(id=1)), {'21-3343353-GAGA-G', '1-46859832-G-A', '1-1562437-G-C'})

        logger_info_calls = [
            mock.call(u'Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call(u'Updated 3 variants for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call(u'  1kg project n\xe5me with uni\xe7\xf8de: Updated 3 variants')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)
        mock_get_variants.reset_mock()
        mock_logger.reset_mock()

        # Test for all projects and no specific family ids
        call_command('reload_saved_variant_json')

        self.assertEqual(mock_get_variants.call_count, 2)
        mock_get_variants.assert_has_calls([
            mock.call(
                set(Family.objects.filter(id__in=[1, 2])),
                {'21-3343353-GAGA-G', '1-46859832-G-A', '1-1562437-G-C', '12-48367227-TC-T'},
            ),
            mock.call(set(Family.objects.filter(id=11)), {'12-48367227-TC-T', 'prefix_19107_DEL'})
        ], any_order=True)

        logger_info_calls = [
            mock.call(u'Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call(u'Updated 4 variants for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call(u'Project: Empty Project'),
            mock.call(u'Updated 0 variants for project Empty Project'),
            mock.call(u'Project: Test Reprocessed Project'),
            mock.call(u'Updated 2 variants for project Test Reprocessed Project'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call(u'  1kg project n\xe5me with uni\xe7\xf8de: Updated 4 variants'),
            mock.call(u'  Test Reprocessed Project: Updated 2 variants')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)
        mock_get_variants.reset_mock()
        mock_logger.reset_mock()

        # Test with an exception.
        mock_get_variants.side_effect = Exception("Database error.")
        call_command('reload_saved_variant_json',
                     PROJECT_GUID,
                     '--family-id={}'.format(FAMILY_ID))

        mock_get_variants.assert_called_with(
            set(Family.objects.filter(id=1)), {'21-3343353-GAGA-G', '1-46859832-G-A', '1-1562437-G-C'})

        logger_info_calls = [
            mock.call(u'Project: 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Done'),
            mock.call('Summary: '),
            mock.call(u'1 failed projects'),
            mock.call(u'  1kg project n\xe5me with uni\xe7\xf8de: Database error.')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)

        mock_logger.error.assert_called_with(u'Error in project 1kg project n\xe5me with uni\xe7\xf8de: Database error.')
