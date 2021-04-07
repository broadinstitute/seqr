import mock

from django.core.management import call_command
from django.test import TestCase

from seqr.models import IgvSample


class CheckBamCramPathsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def setUp(self):
        existing_sample = IgvSample.objects.first()
        IgvSample.objects.create(
            individual=existing_sample.individual,
            sample_type=IgvSample.SAMPLE_TYPE_GCNV,
            file_path='gs://missing-bucket/missing_file',
        )

    @mock.patch('seqr.management.commands.check_bam_cram_paths.does_file_exist')
    @mock.patch('seqr.management.commands.check_bam_cram_paths.logger')
    def test_command_with_project(self, mock_logger, mock_does_file_exist):
        mock_does_file_exist.return_value = False
        call_command('check_bam_cram_paths', '1kg project n\u00e5me with uni\u00e7\u00f8de')
        self._check_results(1, mock_logger, mock_does_file_exist)

    @mock.patch('seqr.management.commands.check_bam_cram_paths.does_file_exist')
    @mock.patch('seqr.management.commands.check_bam_cram_paths.logger')
    def test_command_with_other_project(self, mock_logger, mock_does_file_exist):
        mock_does_file_exist.return_value = False
        call_command('check_bam_cram_paths', '1kg project')
        self.assertEqual(IgvSample.objects.filter(file_path='').count(), 0)
        self.assertEqual(IgvSample.objects.count(), 2)

        calls = [
            mock.call('---- DONE ----'),
            mock.call('Checked 0 samples'),
        ]
        mock_logger.info.assert_has_calls(calls)

    @mock.patch('seqr.management.commands.check_bam_cram_paths.does_file_exist')
    @mock.patch('seqr.management.commands.check_bam_cram_paths.logger')
    def test_command(self, mock_logger, mock_does_file_exist):
        mock_does_file_exist.return_value = False
        call_command('check_bam_cram_paths')
        self._check_results(1, mock_logger, mock_does_file_exist)

    @mock.patch('seqr.management.commands.check_bam_cram_paths.does_file_exist')
    @mock.patch('seqr.management.commands.check_bam_cram_paths.logger')
    def test_dry_run_arg(self, mock_logger, mock_does_file_exist):
        mock_does_file_exist.return_value = False
        call_command('check_bam_cram_paths', '--dry-run')
        self._check_results(0, mock_logger, mock_does_file_exist)

    def _check_results(self, num_paths_deleted, mock_logger, mock_does_file_exist):
        self.assertEqual(IgvSample.objects.filter(file_path='').count(), num_paths_deleted)
        self.assertEqual(IgvSample.objects.count(), 2)

        mock_does_file_exist.assert_called_with("gs://missing-bucket/missing_file")

        calls = [
            mock.call('Individual: NA19675_1  file not found: gs://missing-bucket/missing_file'),
            mock.call('---- DONE ----'),
            mock.call('Checked 1 samples'),
            mock.call('1 files not found:'),
            mock.call('   1 in 1kg project nåme with uniçøde'),
        ]
        mock_logger.info.assert_has_calls(calls)
