# -*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase

from seqr.models import Project

PROJECT_NAME = u'1kg project n\u00e5me with uni\u00e7\u00f8de'


class ResetCachedSearchResultsTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.reset_cached_search_results.reset_cached_search_results')
    @mock.patch('seqr.management.commands.reset_cached_search_results.logger')
    def test_command(self, mock_logger, mock_reset_cached_search_results):
        # Test command with a --project argument
        call_command('reset_cached_search_results', u'--project={}'.format(PROJECT_NAME))
        project = Project.objects.get(name=PROJECT_NAME)
        mock_reset_cached_search_results.assert_called_with(project = project)
        mock_logger.info.assert_called_with(u'Reset cached search results for {}'.format(PROJECT_NAME))

        # Test command without any arguments
        call_command('reset_cached_search_results')
        mock_reset_cached_search_results.assert_called_with(project=None)
        mock_logger.info.assert_called_with('Reset cached search results for all projects')
