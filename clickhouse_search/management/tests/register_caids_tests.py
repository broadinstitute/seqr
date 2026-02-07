import mock
import responses
from django.core.management import call_command
from django.test import TestCase
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL

from reference_data.models import DataVersions


@mock.patch("clickhouse_search.management.commands.register_caids.safe_post_to_slack")
class RegisterCaidsTest(TestCase):
    databases = "__all__"
    fixtures = ["variant_details_for_update"]

    @responses.activate
    def test_register_caids(self, mock_safe_post_to_slack):
        call_command("register_caids", batch_size=3)
        mock_safe_post_to_slack.assert_has_calls([
            mock.call(SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, "Successfully called 38/ClingenAlleleRegistry for variants 3 -> 10."),
        ])
        dv = DataVersions.objects.get(data_model_name='37/ClingenAlleleRegistry')
        self.assertEqual(dv.version, '0')
        dv = DataVersions.objects.get(data_model_name='38/ClingenAlleleRegistry')
        self.assertEqual(dv.version, '10')