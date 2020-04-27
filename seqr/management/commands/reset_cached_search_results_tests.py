# -*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase

PROJECT_NAME = '1kg project'


class ResetCachedSearchResultsTest(TestCase):
    @mock.patch('seqr.management.commands.reset_cached_search_results.reset_cached_search_results')
    @mock.patch('seqr.management.commands.reset_cached_search_results.Project')
    @mock.patch('seqr.management.commands.reset_cached_search_results.logger')
    def test_command(self, mock_logger, mock_project, mock_reset_cached_search_results):
        # Test command with a --project argument
        mock_project.objects.get.side_effect = [PROJECT_NAME]
        call_command('reset_cached_search_results', '--project={}'.format(PROJECT_NAME))
        mock_project.objects.get.assert_called_with(name=PROJECT_NAME)
        mock_reset_cached_search_results.assert_called_with(project = PROJECT_NAME)
        mock_logger.info.assert_called_with('Reset cached search results for {}'.format(PROJECT_NAME))

        # Test command without any arguments
        call_command('reset_cached_search_results')
        mock_reset_cached_search_results.assert_called_with(project=None)
        mock_logger.info.assert_called_with('Reset cached search results for all projects')
