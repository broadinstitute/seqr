#-*- coding: utf-8 -*-
import mock

from django.core.management import call_command, CommandError
from django.test import TestCase

PROJECT_NAME = '1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
FAMILY_GUID = 'F000001_1'


@mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
class ReloadSavedVariantJsonTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.utils.variant_utils.logger')
    @mock.patch('seqr.utils.search.elasticsearch.es_utils.get_es_variants_for_variant_ids')
    def test_with_param_command(self, mock_get_variants, mock_logger):
        mock_get_variants.side_effect = lambda samples, genome_version, variant_ids, user: \
            [{'variantId': variant_id, 'familyGuids': sorted({sample.individual.family.guid for sample in samples}) if samples else ['F000012_12']}
             for variant_id in variant_ids]

        # Test with a specific project and a family id.
        call_command('reload_saved_variant_json',
                     PROJECT_NAME,
                     '--family-guid={}'.format(FAMILY_GUID))

        mock_get_variants.assert_called_with(mock.ANY, '37', ['1-46859832-G-A','21-3343353-GAGA-G'], None)
        self.assertSetEqual(set(mock_get_variants.call_args_list[0].args[0].values_list('id', flat=True)), {129, 130})

        logger_info_calls = [
            mock.call('Updated 2 variants in 1 families for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Reload Summary: '),
            mock.call('  1kg project n\xe5me with uni\xe7\xf8de: Updated 2 variants')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)
        mock_get_variants.reset_mock()
        mock_logger.reset_mock()

        # Test for all projects and no specific family ids
        call_command('reload_saved_variant_json')

        self.assertEqual(mock_get_variants.call_count, 3)
        mock_get_variants.assert_has_calls([
            mock.call(
                mock.ANY, '37', ['1-248367227-TC-T', '1-46859832-G-A', '21-3343353-GAGA-G'], None,
            ),
            mock.call(mock.ANY, '37', ['1-248367227-TC-T', 'prefix_19107_DEL'], None),
            mock.call(mock.ANY, '38',  ['1-248367227-TC-T'], None)
        ])
        self.assertSetEqual(set(mock_get_variants.call_args_list[0].args[0].values_list('id', flat=True)), {
            129, 130, 132, 133, 134, 145, 146, 148, 149,
        })
        self.assertSetEqual(set(mock_get_variants.call_args_list[1].args[0].values_list('id', flat=True)), set())
        self.assertSetEqual(set(mock_get_variants.call_args_list[2].args[0].values_list('id', flat=True)), {147, 173, 174})

        logger_info_calls = [
            mock.call('Reloading saved variants in 4 projects'),
            mock.call('Updated 3 variants for project 1kg project n\xe5me with uni\xe7\xf8de'),
            mock.call('Updated 2 variants for project Test Reprocessed Project'),
            mock.call('Updated 1 variants for project Non-Analyst Project'),
            mock.call('Reload Summary: '),
            mock.call('  1kg project n\xe5me with uni\xe7\xf8de: Updated 3 variants'),
            mock.call('  Test Reprocessed Project: Updated 2 variants'),
            mock.call('  Non-Analyst Project: Updated 1 variants'),
            mock.call('Skipped the following 1 project with no saved variants: Empty Project'),
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)
        mock_get_variants.reset_mock()
        mock_logger.reset_mock()

        # Test with an exception.
        mock_get_variants.side_effect = Exception("Database error.")
        call_command('reload_saved_variant_json',
                     PROJECT_GUID,
                     '--family-guid={}'.format(FAMILY_GUID))

        mock_get_variants.assert_called_with(mock.ANY, '37', ['1-46859832-G-A', '21-3343353-GAGA-G'], None)
        self.assertSetEqual(set(mock_get_variants.call_args_list[0].args[0].values_list('id', flat=True)), {129, 130})

        logger_info_calls = [
            mock.call('Reload Summary: '),
            mock.call('1 failed projects'),
            mock.call('  1kg project n\xe5me with uni\xe7\xf8de: Database error.')
        ]
        mock_logger.info.assert_has_calls(logger_info_calls)

        mock_logger.error.assert_called_with('Error reloading variants in 1kg project n\xe5me with uni\xe7\xf8de: Database error.')


@mock.patch('clickhouse_search.search.CLICKHOUSE_SERVICE_HOSTNAME', 'testhost')
class ClickhouseReloadSavedVariantJsonTest(TestCase):

    fixtures = ['users', '1kg_project']

    def test_command(self):
        with self.assertRaises(ValueError) as ce:
            call_command('reload_saved_variant_json', PROJECT_NAME)
        self.assertEqual(str(ce.exception), 'handle is disabled without the elasticsearch backend')


