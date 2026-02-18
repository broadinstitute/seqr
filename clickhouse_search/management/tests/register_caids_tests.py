import mock
import responses
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from settings import SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL


from clickhouse_search.management.commands.register_caids import ALLELE_REGISTRY_HEADERS
from clickhouse_search.models.search_models import (
    VariantDetailsSnvIndel,
)
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
                        'end': 91511686,
                        'referenceAllele': 'T',
                        'start': 91511686,
                    },
                ],
                'referenceGenome': 'GRCh38',
            },
        ],
        'externalRecords': {
            'gnomAD_4': [{'id': '1-91511686-T-G'}],
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
                        'allele': 'A',
                        'end': 10146,
                        'referenceAllele': 'ACC',
                        'start': 10146,
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
        'message': '1\t10469\trs370233998\tC\tG\t.\t.\t.',
    },
    {
        '@id': 'http://reg.genome.network/allele/CAXXX',
        'genomicAlleles': [
            {
                'chromosome': '1',
                'coordinates': [
                    {
                        # missing allele and referenceAllele
                        'end': 10131,
                        'start': 10131,
                    },
                ],
                'referenceGenome': 'GRCh38',
            },
        ],
    },
]

@mock.patch('clickhouse_search.management.commands.register_caids.logger')
@mock.patch("clickhouse_search.management.commands.register_caids.safe_post_to_slack")
class RegisterCaidsEmptyDatabaseTest(TestCase):
    databases = "__all__"
    fixtures = []

    @responses.activate
    def test_register_caids(self, mock_safe_post_to_slack, mock_logger):
        responses.add(
            responses.PUT,
            "https://reg.genome.network/alleles",
            match=[
                responses.matchers.query_param_matcher({
                    "file": "vcf",
                    "fields": "none @id genomicAlleles externalRecords.gnomAD_4.id",
                }, strict_match=False),
            ],
            status=200,
            json=MOCK_RESPONSE
        )
        call_command("register_caids", batch_size=3)
        mock_logger.info.assert_called_with(
            'Attempting to register caids from key: 0'
        )
        mock_logger.warning.assert_not_called()



@mock.patch('clickhouse_search.management.commands.register_caids.logger')
@mock.patch("clickhouse_search.management.commands.register_caids.safe_post_to_slack")
class RegisterCaidsTest(TestCase):
    databases = "__all__"
    fixtures = ["variant_details_for_update"]

    @responses.activate
    def test_bad_responses(self, mock_safe_post_to_slack, mock_logger):
        responses.add(
            responses.PUT,
            "https://reg.genome.network/alleles",
            match=[
                responses.matchers.query_param_matcher({
                    "file": "vcf",
                    "fields": "none @id genomicAlleles externalRecords.gnomAD_4.id",
                }, strict_match=False),
            ],
            status=200,
            json={'errorType': 'InternalServerError'}
        )
        with self.assertRaisesMessage(CommandError, 'Failed in 38/ClingenAlleleRegistry curr_key: 3'):
            call_command("register_caids", batch_size=5)
        mock_safe_post_to_slack.assert_not_called()

        responses.reset()
        mock_safe_post_to_slack.reset_mock()
        mock_logger.reset_mock()

        responses.add(
            responses.PUT,
            "https://reg.genome.network/alleles",
            match=[
                responses.matchers.query_param_matcher({
                    "file": "vcf",
                    "fields": "none @id genomicAlleles externalRecords.gnomAD_4.id",
                }, strict_match=False),
            ],
            status=200,
            json={'non': 'list'}
        )
        with self.assertRaisesMessage(CommandError, 'Failed in 38/ClingenAlleleRegistry curr_key: 3'):
            call_command("register_caids", batch_size=5)
        mock_safe_post_to_slack.assert_not_called()
        mock_logger.exception.assert_called_with(
            'Failed in 38/ClingenAlleleRegistry curr_key: 3'
        )

    @responses.activate
    def test_failure(self, mock_safe_post_to_slack, mock_logger):
        responses.add(
            responses.PUT,
            "https://reg.genome.network/alleles",
            match=[
                responses.matchers.query_param_matcher({
                    "file": "vcf",
                    "fields": "none @id genomicAlleles externalRecords.gnomAD_4.id",
                }, strict_match=False),
            ],
            status=500,
        )
        with self.assertRaisesMessage(CommandError, 'Failed in 38/ClingenAlleleRegistry curr_key: 3'):
            call_command("register_caids", batch_size=5)
        mock_safe_post_to_slack.assert_not_called()
        mock_logger.exception.assert_called_with(
            'Failed in 38/ClingenAlleleRegistry curr_key: 3'
        )
        dv = DataVersions.objects.get(data_model_name='38/ClingenAlleleRegistry')
        self.assertEqual(dv.version, '3')

    @responses.activate
    def test_register_caids(self, mock_safe_post_to_slack, mock_logger):
        responses.add(
            responses.PUT,
            "https://reg.genome.network/alleles",
            match=[
                responses.matchers.query_param_matcher({
                    "file": "vcf",
                    "fields": "none @id genomicAlleles externalRecords.gnomAD_4.id",
                }, strict_match=False),
            ],
            status=200,
            json=MOCK_RESPONSE
        )
        call_command("register_caids", batch_size=3)
        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(
            [call.request.body for call in responses.calls],
            [
                "\n".join(
                    [
                        *ALLELE_REGISTRY_HEADERS['38'],
                        '1\t91511686\t.\tT\tG\t.\t.\t.',
                        '1\t10146\t.\tACC\tA\t.\t.\t.',
                        '1\t94818\t.\tT\tC\t.\t.\t.',
                    ]
                ) + "\n",
                "\n".join(
                    [
                        *ALLELE_REGISTRY_HEADERS['38'],
                        '7\t143270172\t.\tA\tG\t.\t.\t.',
                        '7\t9310123\t.\tT\tC\t.\t.\t.',
                    ]
                ) + "\n",
            ],
        )
        mock_safe_post_to_slack.assert_has_calls([
            mock.call(SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL, "Successfully called 38/ClingenAlleleRegistry for variants 3 -> 10."),
        ])
        dv = DataVersions.objects.get(data_model_name='37/ClingenAlleleRegistry')
        self.assertEqual(dv.version, '11')
        dv = DataVersions.objects.get(data_model_name='38/ClingenAlleleRegistry')
        self.assertEqual(dv.version, '10')
        mock_logger.info.assert_called_with(
            "2 registered variant(s) cannot be mapped back to ours. \n"
            "First unmappable variant:\n{'@id': 'http://reg.genome.network/allele/CA16716503', 'genomicAlleles': [{'chromosome': '1', 'coordinates': [{'allele': 'C', 'end': 10131, 'referenceAllele': '', 'start': 10131}], 'referenceGenome': 'GRCh38'}]}"
        )
        mock_logger.warning.assert_called_with(
            '1 failed. First error: \n'
            'TYPE: InternalServerError\n'
            'DESCRIPTION: Given allele cannot be mapped in consistent way to reference genome.\n'
            'MESSAGE: 1\t10469\trs370233998\tC\tG\t.\t.\t.\n'
            'INPUT_LINE: Cannot align NC_000001.10 [10468,10469).',
        )
        vd = VariantDetailsSnvIndel.objects.get(variant_id='1-91511686-T-G')
        self.assertEqual(vd.caid, 'CA997563840')

        # Ensure re-calling is a no-op
        mock_safe_post_to_slack.reset_mock()
        mock_logger.reset_mock()
        call_command("register_caids", batch_size=3)
        mock_logger.info.assert_called_with(
            'Attempting to register caids from key: 10',
        )
        mock_logger.warning.assert_not_called()
        mock_safe_post_to_slack.assert_not_called()
