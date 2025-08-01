from django.core.management import call_command
from django.core.management.base import CommandError
import json
import mock
import responses

from seqr.views.utils.test_utils import AnvilAuthenticationTestCase
from seqr.models import Sample, SavedVariant

MOCK_HAIL_HOST = 'test-hail-host'
MOCK_HAIL_ORIGIN = f'http://{MOCK_HAIL_HOST}'


@mock.patch('seqr.utils.search.hail_search_utils.HAIL_BACKEND_SERVICE_HOSTNAME', MOCK_HAIL_HOST)
class ReloadVariantAnnotationsTest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project']

    CLICKHOUSE_HOSTNAME = None

    @responses.activate
    def test_command(self):
        responses.add(responses.POST, f'{MOCK_HAIL_ORIGIN}:5000/multi_lookup', status=200, json={
            'results': [
                {'variantId': '1-46859832-G-A', 'updated_new_field': 'updated_value', 'rsid': 'rs123'},
                {'variantId': '1-248367227-TC-T', 'updated_field': 'updated_value'},
            ],
        })

        # Test errors
        with self.assertRaises(CommandError) as ce:
            call_command('reload_saved_variant_annotations')
        self.assertEqual(str(ce.exception), 'Error: the following arguments are required: data_type, genome_version, chromosomes')

        with self.assertRaises(CommandError) as ce:
            call_command('reload_saved_variant_annotations', 'SV', 'GRCh37')
        self.assertEqual(str(ce.exception), "Error: argument data_type: invalid choice: 'SV' (choose from 'MITO', 'SNV_INDEL', 'SV_WES', 'SV_WGS')")

        # Test success
        self.reset_logs()
        call_command('reload_saved_variant_annotations', 'SNV_INDEL', 'GRCh37')

        self.assert_json_logs(user=None, expected=[
            ('Reloading shared annotations for 2 SNV_INDEL GRCh37 saved variants in chromosome 1 (2 unique)', None),
            ('Fetched 2 additional variants in chromosome 1', None),
            ('update 2 SavedVariants', {'dbUpdate': {
                'dbEntity': 'SavedVariant',
                'entityIds': ['SV0000002_1248367227_r0390_100', 'SV0059956_11560662_f019313_1'],
                'updateFields': ['saved_variant_json'],
                'updateType': 'bulk_update'},
            }),
        ] + [(f'No additional SNV_INDEL GRCh37 saved variants to update in chromosome {chrom}', None) for chrom in ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20']] + [
            ('Reloading shared annotations for 1 SNV_INDEL GRCh37 saved variants in chromosome 21 (1 unique)', None),
            ('Fetched 2 additional variants in chromosome 21', None),
        ] + [(f'No additional SNV_INDEL GRCh37 saved variants to update in chromosome {chrom}', None) for chrom in ['22', 'X', 'Y', 'M']])

        self.assertEqual(len(responses.calls), 2)
        for call in responses.calls:
            self.assertEqual(call.request.url, f'{MOCK_HAIL_ORIGIN}:5000/multi_lookup')
            self.assertEqual(call.request.headers.get('From'), 'manage_command')
        self.assertDictEqual(json.loads(responses.calls[0].request.body), {
            'genome_version': 'GRCh37',
            'data_type': 'SNV_INDEL',
            'variant_ids': [['1', 46859832, 'G', 'A'], ['1', 248367227, 'TC', 'T']],
        })
        self.assertDictEqual(json.loads(responses.calls[1].request.body), {
            'genome_version': 'GRCh37',
            'data_type': 'SNV_INDEL',
            'variant_ids': [['21', 3343353, 'GAGA', 'G']],
        })

        annotation_updated_json_1 = SavedVariant.objects.get(guid='SV0000002_1248367227_r0390_100').saved_variant_json
        self.assertEqual(len(annotation_updated_json_1), 17)
        self.assertListEqual(annotation_updated_json_1['familyGuids'], ['F000001_1'])
        self.assertEqual(annotation_updated_json_1['updated_field'], 'updated_value')

        annotation_updated_json_2 = SavedVariant.objects.get(guid='SV0059956_11560662_f019313_1').saved_variant_json
        self.assertEqual(len(annotation_updated_json_2), 16)
        self.assertEqual(annotation_updated_json_2['updated_new_field'], 'updated_value')
        self.assertEqual(annotation_updated_json_2['rsid'], 'rs123')
        self.assertEqual(annotation_updated_json_2['mainTranscriptId'], 'ENST00000505820')
        self.assertEqual(len(annotation_updated_json_2['genotypes']), 3)

        # Test chromosome subset
        responses.calls.reset()
        self.reset_logs()
        call_command('reload_saved_variant_annotations', 'SNV_INDEL', 'GRCh37', '3', '21')

        self.assert_json_logs(user=None, expected=[(log, None) for log in [
            'No additional SNV_INDEL GRCh37 saved variants to update in chromosome 3',
            'Reloading shared annotations for 1 SNV_INDEL GRCh37 saved variants in chromosome 21 (1 unique)',
            'Fetched 2 additional variants in chromosome 21',
        ]])

        self.assertEqual(len(responses.calls), 1)
        self.assertDictEqual(json.loads(responses.calls[0].request.body), {
            'genome_version': 'GRCh37',
            'data_type': 'SNV_INDEL',
            'variant_ids': [['21', 3343353, 'GAGA', 'G']],
        })

        responses.calls.reset()
        self.reset_logs()
        call_command('reload_saved_variant_annotations', 'SNV_INDEL', 'GRCh37', '3', '6')
        self.assert_json_logs(user=None, expected=[
            (f'No additional SNV_INDEL GRCh37 saved variants to update in chromosome {chrom}', None)
            for chrom in [3, 6]
        ])
        self.assertEqual(len(responses.calls), 0)

        # Test SVs
        responses.calls.reset()
        Sample.objects.filter(guid='S000147_na21234').update(individual_id=20)
        call_command('reload_saved_variant_annotations', 'SV_WGS', 'GRCh37')

        self.assertEqual(len(responses.calls), 1)
        self.assertDictEqual(json.loads(responses.calls[0].request.body), {
            'genome_version': 'GRCh37',
            'data_type': 'SV_WGS',
            'variant_ids': ['prefix_19107_DEL'],
        })


class ClickhouseReloadVariantAnnotationsTest(AnvilAuthenticationTestCase):

    fixtures = ['users', '1kg_project']

    def test_command(self):
        with self.assertRaises(CommandError) as ce:
            call_command('reload_saved_variant_annotations', 'SNV_INDEL', 'GRCh37')
        self.assertEqual(str(ce.exception), 'Reloading variant annotations is not supported in clickhouse')

