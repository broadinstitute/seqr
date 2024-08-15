# -*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase

from seqr.models import Family, VariantSearchResults

PROJECT_NAME = '1kg project n\u00e5me with uni\u00e7\u00f8de'
EMPTY_PROJECT_NAME = 'Empty Project'


class ResetCachedSearchResultsTest(TestCase):
    fixtures = ['users', '1kg_project', 'variant_searches']

    @classmethod
    def setUpTestData(cls):
        result = VariantSearchResults.objects.create(search_hash='abc', variant_search_id=79516)
        result.families.set(Family.objects.filter(pk=1))
        cls.result_guid = result.guid

    @mock.patch('seqr.views.utils.variant_utils.redis.StrictRedis')
    @mock.patch('seqr.views.utils.variant_utils.logger')
    @mock.patch('seqr.management.commands.reset_cached_search_results.logger')
    def test_command(self, mock_command_logger, mock_utils_logger, mock_redis):
        mock_redis.return_value.keys.side_effect = lambda pattern: [pattern] if pattern != 'variant_lookup_results__*' else []

        # Test command with a --project argument
        call_command('reset_cached_search_results', '--project={}'.format(PROJECT_NAME))
        mock_redis.return_value.delete.assert_called_with('search_results__{}*'.format(self.result_guid))
        mock_utils_logger.info.assert_called_with('Reset 1 cached results')
        mock_command_logger.info.assert_called_with('Reset cached search results for {}'.format(PROJECT_NAME))

        # Test for empty project
        mock_redis.reset_mock()
        call_command('reset_cached_search_results', '--project={}'.format(EMPTY_PROJECT_NAME))
        mock_redis.return_value.delete.assert_not_called()
        mock_utils_logger.info.assert_called_with('No cached results to reset')
        mock_command_logger.info.assert_called_with('Reset cached search results for {}'.format(EMPTY_PROJECT_NAME))

        # Test command without any arguments
        mock_redis.reset_mock()
        call_command('reset_cached_search_results')
        mock_redis.return_value.delete.assert_called_with('search_results__*')
        mock_utils_logger.info.assert_called_with('Reset 1 cached results')
        mock_command_logger.info.assert_called_with('Reset cached search results for all projects')

        # Test command for reset metadata
        mock_redis.reset_mock()
        mock_redis.return_value.keys.side_effect = lambda pattern: [pattern]
        call_command('reset_cached_search_results', '--reset-index-metadata')
        mock_redis.return_value.delete.assert_called_with('search_results__*', 'variant_lookup_results__*', 'index_metadata__*')
        mock_utils_logger.info.assert_called_with('Reset 3 cached results')
        mock_command_logger.info.assert_called_with('Reset cached search results for all projects')

        # Test with connection error
        mock_redis.side_effect = Exception('invalid redis')
        call_command('reset_cached_search_results')
        mock_utils_logger.error.assert_called_with('Unable to reset cached search results: invalid redis')
        mock_command_logger.info.assert_called_with('Reset cached search results for all projects')
