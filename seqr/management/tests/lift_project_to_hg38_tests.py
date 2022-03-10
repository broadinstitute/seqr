#-*- coding: utf-8 -*-
import mock
from copy import deepcopy
from django.core.management.base import CommandError
from seqr.models import Family
from pyliftover.liftover import LiftOver
from seqr.views.utils.test_utils import VARIANTS, SINGLE_VARIANT

from django.core.management import call_command
from django.test import TestCase

PROJECT_NAME = '1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
ELASTICSEARCH_INDEX = 'test_index'
SAMPLE_TYPE = 'WES'
GENOME_VERSION = '38'
SAMPLE_IDS = ["NA19679", "NA19675_1", "NA19678", "HG00731", "HG00732", "HG00733"]

liftover_to_38 = LiftOver('hg19', 'hg38')

LIFT_MAP = {
    21003343353: [('chr21', 3343400)],
    1248367227: [('chr1', 248203925)],
    1001562437: [('chr1',   1627057)],
    1001560662: [('chr1',  46394160)],
}


def mock_convert_coordinate(chrom, pos):
    pos = int(chrom.replace('chr', ''))*int(1e9) + pos
    return(LIFT_MAP[pos])


@mock.patch('seqr.management.commands.lift_project_to_hg38.logger')
@mock.patch('seqr.management.commands.lift_project_to_hg38.validate_index_metadata_and_get_elasticsearch_index_samples')
class LiftProjectToHg38Test(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.lift_project_to_hg38.input')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_es_variants_for_variant_tuples')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.LiftOver')
    def test_command(self, mock_liftover, mock_get_es_variants, mock_input, mock_get_es_samples, mock_logger):
        mock_get_es_samples.return_value = SAMPLE_IDS, SAMPLE_TYPE
        mock_get_es_variants.return_value = VARIANTS
        mock_liftover_to_38 = mock_liftover.return_value
        mock_liftover_to_38.convert_coordinate.side_effect = mock_convert_coordinate
        mock_input.return_value = 'y'
        call_command('lift_project_to_hg38', '--project={}'.format(PROJECT_NAME),
                     '--es-index={}'.format(ELASTICSEARCH_INDEX))

        calls = [
            mock.call('Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 4 variants (skipping 0 that are already lifted)'),
            mock.call('Successfully lifted over 3 variants'),
            mock.call('Successfully updated 3 variants'),
            mock.call('---Done---'),
            mock.call('Succesfully lifted over 3 variants. Skipped 3 failed variants. Family data not updated for 0 variants')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_get_es_samples.assert_called_with(ELASTICSEARCH_INDEX, genome_version=GENOME_VERSION)

        calls = [
            mock.call('chr21', 3343353),
            mock.call('chr1', 1562437),
            mock.call('chr1', 248367227),
            mock.call('chr1', 1560662),
        ]
        mock_liftover_to_38.convert_coordinate.assert_has_calls(calls, any_order = True)

        families = {family for family in Family.objects.filter(pk__in = [1, 2])}
        self.assertSetEqual(families, mock_get_es_variants.call_args.args[0])
        self.assertSetEqual(set([(1001627057, 'G', 'C'), (21003343400, 'GAGA', 'G'), (1248203925, 'TC', 'T'),
                                 (1046394160, 'G', 'A')]), set(mock_get_es_variants.call_args.args[1]))

        # Test discontinue on lifted variants
        mock_logger.reset_mock()
        mock_input.side_effect = 'n'
        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', '--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(str(ce.exception), 'Error: found 1 saved variants already on Hg38')

        calls = [
            mock.call('Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
        ]
        mock_logger.info.assert_has_calls(calls)

    def test_command_error_unmatched_sample(self, mock_get_es_samples, mock_logger):
        mock_get_es_samples.return_value = ['ID_NOT_EXIST'], SAMPLE_TYPE

        with self.assertRaises(ValueError) as ce:
            call_command('lift_project_to_hg38', '--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(str(ce.exception), 'Matches not found for ES sample ids: ID_NOT_EXIST.')

        calls = [
            mock.call('Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_get_es_samples.assert_called_with(ELASTICSEARCH_INDEX, genome_version=GENOME_VERSION)

    def test_command_error_missing_indvididuals(self, mock_get_es_samples, mock_logger):
        mock_get_es_samples.return_value = ['NA19675_1'], SAMPLE_TYPE

        with self.assertRaises(ValueError) as ce:
            call_command('lift_project_to_hg38', '--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(str(ce.exception),
            'The following families are included in the callset but are missing some family members: 1 (NA19678).')

        calls = [
            mock.call('Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_get_es_samples.assert_called_with(ELASTICSEARCH_INDEX, genome_version=GENOME_VERSION)

    def test_command_error_missing_families(self, mock_get_es_samples, mock_logger):
        mock_get_es_samples.return_value = ['HG00731', 'HG00732', 'HG00733'], SAMPLE_TYPE

        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', '--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(str(ce.exception),
            'The following families have saved variants but are missing from the callset: 1.')

        calls = [
            mock.call('Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_get_es_samples.assert_called_with(ELASTICSEARCH_INDEX, genome_version=GENOME_VERSION)

    @mock.patch('seqr.management.commands.lift_project_to_hg38.input')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_es_variants_for_variant_tuples')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_single_es_variant')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.LiftOver')
    def test_command_other_exceptions(self, mock_liftover, mock_single_es_variants,
            mock_get_es_variants, mock_input, mock_get_es_samples, mock_logger):
        mock_get_es_samples.return_value = SAMPLE_IDS, SAMPLE_TYPE

        # Test discontinue on a failed lift
        mock_liftover_to_38 = mock_liftover.return_value
        mock_liftover_to_38.convert_coordinate.return_value = None
        mock_input.return_value = 'n'
        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', '--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(str(ce.exception), 'Error: unable to lift over 4 variants')

        calls = [
            mock.call('Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 4 variants (skipping 0 that are already lifted)')
        ]
        mock_logger.info.assert_has_calls(calls)

        # Test discontinue on failure of finding a variant in the index
        mock_get_es_variants.return_value = VARIANTS
        mock_liftover_to_38.convert_coordinate.side_effect = mock_convert_coordinate
        mock_logger.reset_mock()
        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', '--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(str(ce.exception), 'Error: unable to find 3 lifted-over variants')

        calls = [
            mock.call('Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 4 variants (skipping 0 that are already lifted)')
        ]
        mock_logger.info.assert_has_calls(calls)

        families = {f for f in Family.objects.filter(pk__in=[1,2])}
        self.assertSetEqual(mock_get_es_variants.call_args.args[0], families)
        self.assertSetEqual(
            set(mock_get_es_variants.call_args.args[1]),
            {(1001627057, 'G', 'C'), (21003343400, 'GAGA', 'G'), (1248203925, 'TC', 'T'), (1046394160, 'G', 'A')}
        )

        # Test discontinue on missing family data while updating the saved variants
        variants = deepcopy(VARIANTS)
        variants.append(SINGLE_VARIANT)
        mock_get_es_variants.return_value = variants
        mock_logger.reset_mock()
        mock_input.side_effect = ['y', 'n']
        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', '--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(str(ce.exception), 'Error: unable to find family data for lifted over variant')

        calls = [
            mock.call('Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 4 variants (skipping 0 that are already lifted)'),
            mock.call('Successfully lifted over 4 variants')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_single_es_variants.return_value = SINGLE_VARIANT
        mock_logger.reset_mock()
        mock_input.reset_mock(side_effect = True)
        mock_input.return_value = 'y'
        call_command('lift_project_to_hg38', '--project={}'.format(PROJECT_NAME),
                     '--es-index={}'.format(ELASTICSEARCH_INDEX))

        calls = [
            mock.call('Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 3 variants (skipping 1 that are already lifted)'),
            mock.call('Successfully lifted over 4 variants'),
            mock.call('Successfully updated 4 variants'),
            mock.call('---Done---'),
            mock.call('Succesfully lifted over 4 variants. Skipped 2 failed variants. Family data not updated for 1 variants')
        ]
        mock_logger.info.assert_has_calls(calls)

        families = [f for f in Family.objects.filter(pk=1)]
        mock_single_es_variants.assert_called_with(families, '1-46394160-G-A', return_all_queried_families=True)
