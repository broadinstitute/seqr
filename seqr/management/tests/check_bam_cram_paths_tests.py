import mock

from django.core.management import call_command
from django.test import TestCase


class CheckBamCramPathsTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.check_bam_cram_paths.logger')
    @mock.patch('seqr.views.utils.dataset_utils.validate_alignment_dataset_path')
    def test_command(self, mock_validate_path, mock_logger):
        call_command('check_bam_cram_paths', '1kg project n\u00e5me with uni\u00e7\u00f8de')

        calls = [
            mock.call('---- DONE ----'),
            mock.call('Checked 1 samples'),
            mock.call('0 failed samples: '),
        ]
        mock_logger.info.assert_has_calls(calls)
        mock_validate_path.assert_called_with("/readviz/NA19675.cram")

        # Test exception
        mock_validate_path.side_effect = Exception('Error accessing "/readviz/NA19675.cram"')
        call_command('check_bam_cram_paths', '1kg project n\u00e5me with uni\u00e7\u00f8de')

        calls = [
            mock.call('Error at /readviz/NA19675.cram (Individual: NA19675_1): Error accessing "/readviz/NA19675.cram" '),
            mock.call('---- DONE ----'),
            mock.call('Checked 1 samples'),
            mock.call('1 failed samples: NA19675_1'),
        ]
        mock_logger.info.assert_has_calls(calls)
        mock_validate_path.assert_called_with("/readviz/NA19675.cram")
