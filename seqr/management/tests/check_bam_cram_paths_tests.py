import mock

from django.core.management import call_command
from django.test import TestCase

from seqr.models import IgvSample


class CheckBamCramPathsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def setUp(self):
        IgvSample.objects.update(file_path='gs://missing-bucket/missing_file.cram')

    @mock.patch('seqr.management.commands.check_bam_cram_paths.logger')
    def test_command_with_project(self, mock_logger):
        call_command('check_bam_cram_paths', '1kg project n\u00e5me with uni\u00e7\u00f8de')

        self._check_results(mock_logger)

    @mock.patch('seqr.management.commands.check_bam_cram_paths.logger')
    def test_command(self, mock_logger):
        # run on just the 1kg project
        call_command('check_bam_cram_paths')

        self._check_results(mock_logger)

    def _check_results(self, mock_logger):
        self.assertEqual(IgvSample.objects.filter(file_path='').count(), 1)
        self.assertEqual(IgvSample.objects.count(), 1)

        calls = [
            mock.call('Individual: NA19675_1  file not found: gs://missing-bucket/missing_file.cram'),
            mock.call('---- DONE ----'),
            mock.call('Checked 1 samples'),
            mock.call('1 files not found:'),
            mock.call('   1 in 1kg project nåme with uniçøde'),
        ]
        mock_logger.info.assert_has_calls(calls)
