import mock

from django.core.management import call_command
from django.test import TestCase
from seqr.models import IgvSample
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL


@mock.patch('seqr.utils.file_utils.subprocess.Popen')
@mock.patch('seqr.utils.communication_utils.safe_post_to_slack')
@mock.patch('seqr.management.commands.check_bam_cram_paths.logger')
class CheckBamCramPathsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_command_with_project(self, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        mock_subprocess.return_value.wait.side_effect = [-1, 0]
        call_command('check_bam_cram_paths', '1kg project n\u00e5me with uni\u00e7\u00f8de')
        self._check_results(True, mock_logger, mock_safe_post_to_slack, mock_subprocess)

    def test_command_with_other_project(self, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        mock_subprocess.return_value.wait.side_effect = [-1, 0]
        call_command('check_bam_cram_paths', '1kg project')
        self.assertEqual(IgvSample.objects.count(), 3)

        calls = [
            mock.call('---- DONE ----'),
            mock.call('Checked 0 samples'),
        ]
        mock_logger.info.assert_has_calls(calls)

    def test_command(self, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        mock_subprocess.return_value.wait.side_effect = [-1, 0]
        call_command('check_bam_cram_paths')
        self._check_results(True, mock_logger, mock_safe_post_to_slack, mock_subprocess)

    def test_dry_run_arg(self, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        mock_subprocess.return_value.wait.side_effect = [-1, 0]
        call_command('check_bam_cram_paths', '--dry-run')
        self._check_results(False, mock_logger, mock_safe_post_to_slack, mock_subprocess)

    def _check_results(self, did_delete, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        igv_file_paths = IgvSample.objects.values_list('file_path', flat=True)
        expected_remaining_files = ['/readviz/NA19675.cram', 'gs://datasets-gcnv/NA20870.bed.gz']
        if not did_delete:
            expected_remaining_files.append('gs://readviz/NA20870.cram')
        self.assertListEqual(sorted(igv_file_paths), expected_remaining_files)

        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://readviz/NA20870.cram', stdout=-1, stderr=-2, shell=True),
            mock.call('gsutil ls gs://datasets-gcnv/NA20870.bed.gz', stdout=-1, stderr=-2, shell=True),
        ], any_order=True)

        calls = [
            mock.call('Individual: NA20870  file not found: gs://readviz/NA20870.cram'),
            mock.call('---- DONE ----'),
            mock.call('Checked 2 samples'),
            mock.call('1 files not found:'),
            mock.call('   1 in 1kg project nåme with uniçøde'),
        ]
        mock_logger.info.assert_has_calls(calls)

        if not did_delete:
            mock_safe_post_to_slack.assert_not_called()
        else:
            self.assertEqual(mock_safe_post_to_slack.call_count, 1)
            mock_safe_post_to_slack.assert_called_with(
                SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
                "Found and removed 1 broken bam/cram path(s)\n\nIn project 1kg project nåme with uniçøde:\n  NA20870   gs://readviz/NA20870.cram")
