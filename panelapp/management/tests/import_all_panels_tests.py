import mock

from django.core.management import call_command
from django.test import TestCase


class ImportAllPanelsTest(TestCase):

    @mock.patch('panelapp.management.commands.import_all_panels.logger')
    @mock.patch('panelapp.management.commands.import_all_panels.import_all_panels')
    def test_import_all_panels(self, mock_import_all_panels, mock_logger):
        call_command('import_all_panels')
        mock_logger.info.assert_has_calls([
            mock.call('Starting import of all gene lists from Panel App [https://panelapp.url/api/v1]'),
            mock.call('---Done---')
        ])
        mock_import_all_panels.assert_called_with(None)
