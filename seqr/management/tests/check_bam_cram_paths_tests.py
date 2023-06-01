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

    def setUp(self):
        existing_sample = IgvSample.objects.first()
        IgvSample.objects.create(
            individual=existing_sample.individual,
            sample_type=IgvSample.SAMPLE_TYPE_GCNV,
            file_path='gs://missing-bucket/missing_file',
        )

    def test_command_with_project(self, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        mock_subprocess.return_value.wait.return_value = -1
        call_command('check_bam_cram_paths', '1kg project n\u00e5me with uni\u00e7\u00f8de')
        self._check_results(1, mock_logger, mock_safe_post_to_slack, mock_subprocess)

    def test_command_with_other_project(self, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        mock_subprocess.return_value.wait.return_value = -1
        call_command('check_bam_cram_paths', '1kg project')
        self.assertEqual(IgvSample.objects.filter(file_path='').count(), 0)
        self.assertEqual(IgvSample.objects.count(), 2)

        calls = [
            mock.call('---- DONE ----'),
            mock.call('Checked 0 samples'),
        ]
        mock_logger.info.assert_has_calls(calls)

    def test_command(self, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        mock_subprocess.return_value.wait.return_value = -1
        call_command('check_bam_cram_paths')
        self._check_results(1, mock_logger, mock_safe_post_to_slack, mock_subprocess)

    def test_dry_run_arg(self, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        mock_subprocess.return_value.wait.return_value = -1
        call_command('check_bam_cram_paths', '--dry-run')
        self._check_results(0, mock_logger, mock_safe_post_to_slack, mock_subprocess)

    def _check_results(self, num_paths_deleted, mock_logger, mock_safe_post_to_slack, mock_subprocess):
        self.assertEqual(IgvSample.objects.filter(file_path='').count(), num_paths_deleted)
        self.assertEqual(IgvSample.objects.count(), 2)
        mock_subprocess.assert_called_with('gsutil ls gs://missing-bucket/missing_file', stdout=-1, stderr=-2, shell=True)

        calls = [
            mock.call('Individual: NA19675_1  file not found: gs://missing-bucket/missing_file'),
            mock.call('---- DONE ----'),
            mock.call('Checked 1 samples'),
            mock.call('1 files not found:'),
            mock.call('   1 in 1kg project nåme with uniçøde'),
        ]
        mock_logger.info.assert_has_calls(calls)

        if num_paths_deleted == 0:
            mock_safe_post_to_slack.assert_not_called()
        else:
            self.assertEqual(mock_safe_post_to_slack.call_count, 1)
            mock_safe_post_to_slack.assert_called_with(
                SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL,
                "Found 1 broken bam/cram path(s)\n\nIn project 1kg project nåme with uniçøde:\n  NA19675_1   gs://missing-bucket/missing_file")
