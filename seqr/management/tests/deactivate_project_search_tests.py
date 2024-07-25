# -*- coding: utf-8 -*-
import mock

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError
from seqr.models import Sample

PROJECT_GUID = 'R0001_1kg'
VARIANT_ID = '21-3343353-GAGA-G'


class DeactivateProjectSearchTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.deactivate_project_search.input')
    @mock.patch('seqr.management.commands.deactivate_project_search.logger')
    def test_command(self, mock_logger, mock_input):
        mock_input.return_value = 'n'

        # Test invalid project
        with self.assertRaises(ObjectDoesNotExist):
            call_command('deactivate_project_search', 'foo')

        # Test user did not confirm.
        with self.assertRaises(CommandError) as e:
            call_command('deactivate_project_search', PROJECT_GUID)
        self.assertEqual(str(e.exception), 'Error: user did not confirm')

        # Test success
        mock_input.return_value = 'y'
        call_command('deactivate_project_search', PROJECT_GUID)
        mock_logger.info.assert_called_with('Deactivated 11 samples')

        active_samples = Sample.objects.filter(individual__family__project__guid=PROJECT_GUID, is_active=True)
        self.assertEqual(active_samples.count(), 0)

        # Re-running has no effect
        call_command('deactivate_project_search', PROJECT_GUID)
        mock_logger.info.assert_called_with('Deactivated 0 samples')
