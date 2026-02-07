import mock
import responses
from django.core.management import call_command
from django.test import TestCase
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL

from reference_data.models import DataVersions

MOCK_RESPONSE = [
    {
        '@id': 'http://reg.genome.network/allele/CA997563840',
        'genomicAlleles': [
            {
                'chromosome': '1',
                'coordinates': [
                    {
                        'allele': '',  # alt allele is ''
                        'end': 91502721,
                        'referenceAllele': 'A',
                        'start': 91502721,
                    },
                ],
                'referenceGenome': 'GRCh38',
            },
        ],
        'externalRecords': {
            'gnomAD_4': [{'id': '1-91502721-G-A'}],
        },  # has gnomad ID
    },
    {
        '@id': 'http://reg.genome.network/allele/CA16716503',
        'genomicAlleles': [
            {
                'chromosome': '1',
                'coordinates': [
                    {
                        'allele': 'C',
                        'end': 10131,
                        'referenceAllele': '',  # ref allele is '' and does not have a gnomad ID
                        'start': 10131,
                    },
                ],
                'referenceGenome': 'GRCh38',
            },
        ],
    },
    {
        '@id': 'http://reg.genome.network/allele/CA997563845',
        'genomicAlleles': [
            {
                'chromosome': '1',
                'coordinates': [
                    {
                        'allele': 'G',
                        'end': 10128,
                        'referenceAllele': 'ACC',
                        'start': 10127,
                    },
                ],
                'referenceGenome': 'GRCh38',
            },
        ],
        'externalRecords': {'gnomAD_4': [{'id': '1-10146-ACC-A'}]},
    },
    {
        'description': 'Given allele cannot be mapped in consistent way to reference genome.',
        'errorType': 'InternalServerError',
        'inputLine': 'Cannot align NC_000001.10 [10468,10469).',
        'message': '1   10469   rs370233998 C   G   .   .   .',
    },
]

@mock.patch('clickhouse_search.management.commands.register_caids.logger')
@mock.patch("clickhouse_search.management.commands.register_caids.safe_post_to_slack")
class RegisterCaidsTest(TestCase):
    databases = "__all__"
    fixtures = ["variant_details_for_update"]

    @responses.activate
    def test_register_caids(self, mock_safe_post_to_slack, mock_logger):
        responses.add(responses.GET, MOCK_RESPONSE, status=200, json=MOCK_RESPONSE)
        call_command("register_caids", batch_size=3)
        mock_safe_post_to_slack.assert_has_calls([
            mock.call(SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, "Successfully called 38/ClingenAlleleRegistry for variants 3 -> 10."),
        ])
        dv = DataVersions.objects.get(data_model_name='37/ClingenAlleleRegistry')
        self.assertEqual(dv.version, '0')
        dv = DataVersions.objects.get(data_model_name='38/ClingenAlleleRegistry')
        self.assertEqual(dv.version, '10')
        mock_logger.info.assert_called_with(
            "1 registered variant(s) cannot be mapped back to ours. "
            f"\nFirst unmappable variant:\n XXX",
        )
        mock_logger.warning.assert_called_with(
            '1 failed. First error: \n'
            'API URL: https://reg.genome.network/alleles?file=vcf&fields=none+@id+genomicAlleles+externalRecords.gnomAD_4.id\n'
            'TYPE: InternalServerError\n'
            'DESCRIPTION: Given allele cannot be mapped in consistent way to reference genome.\n'
            'MESSAGE: 1\t10469\trs370233998\tC\tG\t.\t.\t.\n'
            'INPUT_LINE: Cannot align NC_000001.10 [10468,10469).',
        )