import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

def mock_dbnsfp_gene_handler():
    return "dbnsfp_gene"

def mock_gene_constraint_handler():
    return "gene_constraint"

def mock_primate_ai_handler():
    raise Exception('Primate_AI failed')

def mock_mgi_handler():
    raise Exception('MGI failed')

MOCK_REFERENCE_DATA_SOURCES = [
            ("dbnsfp_gene", mock_dbnsfp_gene_handler),
            ("gene_constraint", mock_gene_constraint_handler),
            ("primate_ai", mock_primate_ai_handler),
            ("mgi", mock_mgi_handler),
            ("hpo", None)
        ]

def raise_exception(msg):
    raise Exception('Bad ' + msg)

@mock.patch('reference_data.management.commands.update_all_reference_data.REFERENCE_DATA_SOURCES')
@mock.patch('reference_data.management.commands.update_all_reference_data.logger')
@mock.patch('reference_data.management.commands.update_all_reference_data.update_records')
@mock.patch('reference_data.management.commands.update_all_reference_data.update_hpo')
@mock.patch('reference_data.management.commands.update_all_reference_data.update_gencode')
@mock.patch('reference_data.management.commands.update_all_reference_data.OmimReferenceDataHandler')
class UpdateAllReferenceDataTest(TestCase):
    fixtures = ['users', 'reference_data']

    def test_update_all_reference_data_command(self, mock_omim, mock_update_gencode, mock_update_hpo, mock_update_records, mock_logger, mock_sources):

        # Test missing required argument
        with self.assertRaises(CommandError) as err:
            call_command('update_all_reference_data')
        self.assertEqual(err.exception.message, u'Error: one of the arguments --omim-key --skip-omim is required')

        # Test update all gencode, no any skips
        mock_omim.return_value = 'omim'
        mock_sources.keys.return_value = ['dbnsfp_gene', 'gene_constraint', 'primate_ai', 'mgi', 'hpo']
        mock_sources.items.return_value = MOCK_REFERENCE_DATA_SOURCES
        call_command('update_all_reference_data', '--omim-key=test_key')

        calls = [
            mock.call(31, reset=True),
            mock.call(29),
            mock.call(28),
            mock.call(27),
            mock.call(19),
        ]
        mock_update_gencode.assert_has_calls(calls)

        mock_omim.assert_called_with('test_key')

        calls = [
            mock.call('omim'),
            mock.call('dbnsfp_gene'),
            mock.call('gene_constraint'),
        ]
        mock_update_records.assert_has_calls(calls)

        mock_update_hpo.assert_called_with()

        calls = [
            mock.call('Done'),
            mock.call('Updated: gencode, omim, dbnsfp_gene, gene_constraint, hpo'),
            mock.call('Failed to Update: primate_ai, mgi')
        ]
        mock_logger.info.assert_has_calls(calls)

        calls = [
            mock.call('unable to update primate_ai: Primate_AI failed'),
            mock.call('unable to update mgi: MGI failed')
        ]
        mock_logger.error.assert_has_calls(calls)

        # Test skipping all
    def test_update_none_reference_data_command(self, mock_omim, mock_update_gencode, mock_update_hpo, mock_update_records, mock_logger, mock_sources):
        mock_sources.keys.return_value = ['dbnsfp_gene', 'gene_constraint', 'primate_ai', 'mgi', 'hpo']
        mock_sources.items.return_value = MOCK_REFERENCE_DATA_SOURCES
        call_command('update_all_reference_data', '--skip-gencode', '--skip-omim', '--skip-dbnsfp-gene', '--skip-gene-constraint', '--skip-primate-ai', '--skip-mgi', '--skip-hpo')

        mock_update_gencode.assert_not_called()

        mock_omim.assert_not_called()

        mock_update_records.assert_not_called()

        mock_update_hpo.assert_not_called()

        mock_logger.info.assert_called_with("Done")

        # Test omim exception
    def test_update_exceptions(self, mock_omim, mock_update_gencode, mock_update_hpo, mock_update_records, mock_logger, mock_sources):
        mock_omim.side_effect = raise_exception
        mock_sources.keys.return_value = ['dbnsfp_gene', 'gene_constraint', 'primate_ai', 'mgi', 'hpo']
        mock_sources.items.return_value = MOCK_REFERENCE_DATA_SOURCES
        call_command('update_all_reference_data', '--skip-gencode', '--omim=test_key', '--skip-dbnsfp-gene', '--skip-gene-constraint', '--skip-primate-ai', '--skip-mgi', '--skip-hpo')

        mock_update_gencode.assert_not_called()

        mock_omim.assert_called_with('test_key')

        mock_update_records.assert_not_called()

        mock_update_hpo.assert_not_called()

        calls = [
            mock.call('Done'),
            mock.call('Failed to Update: omim')
        ]
        mock_logger.info.assert_has_calls(calls)

        mock_logger.error.assert_called_with("unable to update omim: Bad test_key")