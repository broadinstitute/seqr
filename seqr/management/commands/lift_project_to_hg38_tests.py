#-*- coding: utf-8 -*-
import mock
import __builtin__
from copy import deepcopy
from django.core.management.base import CommandError
from seqr.models import Family, Individual, SavedVariant
from pyliftover.liftover import LiftOver
from seqr.views.utils.test_utils import VARIANTS

from django.core.management import call_command
from django.test import TestCase

PROJECT_NAME = u'1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
ELASTICSEARCH_INDEX = 'test_index'
INDEX_METADATA = {
    "gencodeVersion": "25",
    "hail_version": "0.2.24",
    "genomeVersion": "38",
    "sampleType": "WES",
    "sourceFilePath": "test_index_alias_1_path.vcf.gz",
}
SAMPLE_IDS = ["NA19679", "NA19675_1", "NA19678", "HG00731", "HG00732", "HG00733"]

liftover_to_38 = LiftOver('hg19', 'hg38')


# To create a none return value for the variant at pos 1562437
def mock_convert_coordinate(chrom, pos):
    if pos == 1562437:
        return
    return liftover_to_38.convert_coordinate(chrom, pos)

@mock.patch('seqr.management.commands.lift_project_to_hg38.logger')
class LiftProjectToHg38Test(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch.object(__builtin__, 'raw_input')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_elasticsearch_index_samples')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_es_variants_for_variant_tuples')
    def test_command(self, mock_get_es_variants, mock_get_es_samples, mock_input, mock_logger):
        mock_get_es_samples.return_value = SAMPLE_IDS, INDEX_METADATA
        mock_get_es_variants.return_value = VARIANTS
        mock_input.return_value = 'y'
        call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                     '--es-index={}'.format(ELASTICSEARCH_INDEX))

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 4 variants (skipping 0 that are already lifted)'),
            mock.call('Successfully lifted over 3 variants'),
            mock.call('Successfully updated 3 variants'),
            mock.call('---Done---'),
            mock.call('Succesfully lifted over 3 variants. Skipped 4 failed variants. Family data not updated for 0 variants')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_get_es_samples.assert_called_with(ELASTICSEARCH_INDEX)
        mock_get_es_variants.assert_called_with(mock.ANY, [(1001627057, u'G', u'C'), (1046394160, u'G', u'A'), (1248203925, u'TC', u'T'), (2003339582, u'GAGA', u'G')])

        # Test discontinue on lifted variants
        mock_logger.reset_mock()
        mock_input.return_value = 'n'
        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(ce.exception.message, 'Error: found 1 saved variants already on Hg38')

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
        ]
        mock_logger.info.assert_has_calls(calls)

    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_elasticsearch_index_samples')
    def test_command_error_unmatched_sample(self, mock_get_es_samples, mock_logger):
        mock_get_es_samples.return_value = ['ID_NOT_EXIST'], INDEX_METADATA

        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(ce.exception.message, 'Matches not found for ES sample ids: ID_NOT_EXIST.')

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_get_es_samples.assert_called_with(ELASTICSEARCH_INDEX)

    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_elasticsearch_index_samples')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.Individual')
    def test_command_error_missing_indvididuals(self, mock_Individual, mock_get_es_samples, mock_logger):
        mock_get_es_samples.return_value = SAMPLE_IDS, INDEX_METADATA

        mock_ind = mock_Individual.objects.filter.return_value
        mock_exclude_ind = mock_ind.exclude.return_value
        family = Family.objects.get(pk=1)
        mock_exclude_ind.select_related.return_value = [Individual.objects.create(family = family, individual_id = "NO_MATCHED_SAMPLE_IND_ID")]
        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(ce.exception.message, 'The following families are included in the callset but are missing some family members: 1 (NO_MATCHED_SAMPLE_IND_ID).')

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_get_es_samples.assert_called_with(ELASTICSEARCH_INDEX)

    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_elasticsearch_index_samples')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.SavedVariant')
    def test_command_error_missing_families(self, mock_SavedVariant, mock_get_es_samples, mock_logger):
        mock_get_es_samples.return_value = SAMPLE_IDS, INDEX_METADATA

        saved_variants = SavedVariant.objects.filter(pk__in=[1,2,6])
        mock_SavedVariant.objects.filter.return_value = saved_variants

        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(ce.exception.message, 'The following families have saved variants but are missing from the callset: 11.')

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_get_es_samples.assert_called_with(ELASTICSEARCH_INDEX)

    @mock.patch.object(__builtin__, 'raw_input')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_elasticsearch_index_samples')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_es_variants_for_variant_tuples')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.get_single_es_variant')
    @mock.patch('seqr.management.commands.lift_project_to_hg38.LiftOver')
    def test_command_other_exceptions(self, mock_liftover, mock_single_es_variants,
            mock_get_es_variants, mock_get_es_samples, mock_input, mock_logger):
        mock_get_es_samples.return_value = VARIANTS, INDEX_METADATA

        # Test discontinue on a failed lift
        mock_liftover_to_38 = mock_liftover.return_value
        mock_liftover_to_38.convert_coordinate.side_effect = mock_convert_coordinate
        mock_input.side_effect = ['y', 'n']
        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(ce.exception.message, 'Error: unable to lift over 1 variants')

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 3 variants (skipping 1 that are already lifted)')
        ]
        mock_logger.info.assert_has_calls(calls)

        calls = [
            mock.call("chr1", 1562437),
            mock.call("chr1", 248367227),
            mock.call("chr1", 46859832),
        ]
        mock_liftover_to_38.convert_coordinate.assert_has_calls(calls, any_order = True)

        # Test discontinue on failure of finding a variant in the index
        mock_get_es_variants.return_value = VARIANTS[:1]
        mock_logger.reset_mock()
        mock_input.side_effect = ['y', 'y', 'n']
        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(ce.exception.message, 'Error: unable to find 1 lifted-over variants')

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 3 variants (skipping 1 that are already lifted)')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_get_es_variants.assert_called_with(mock.ANY, [(1046394160, u'G', u'A'), (1248203925, u'TC', u'T')])

        # Test discontinue on missing family data while updating the saved variants
        mock_logger.reset_mock()
        mock_input.side_effect = ['y', 'y', 'y', 'n']
        with self.assertRaises(CommandError) as ce:
            call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                    '--es-index={}'.format(ELASTICSEARCH_INDEX))

        self.assertEqual(ce.exception.message, 'Error: unable to find family data for lifted over variant')

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 3 variants (skipping 1 that are already lifted)'),
            mock.call('Successfully lifted over 1 variants')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_single_es_variants.return_value = VARIANTS[1]
        mock_logger.reset_mock()
        mock_input.side_effect = ['y', 'y', 'y', 'y']
        call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                     '--es-index={}'.format(ELASTICSEARCH_INDEX))

        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index'),
            mock.call('Lifting over 3 variants (skipping 1 that are already lifted)'),
            mock.call('Successfully lifted over 1 variants'),
            mock.call('Successfully updated 1 variants'),
            mock.call('---Done---'),
            mock.call('Succesfully lifted over 1 variants. Skipped 2 failed variants. Family data not updated for 1 variants')
        ]
        mock_logger.info.assert_has_calls(calls)

        families = [f for f in Family.objects.filter(pk=1)]
        mock_single_es_variants.assert_called_with(families, '1-248367227-G-A', return_all_queried_families=True)
