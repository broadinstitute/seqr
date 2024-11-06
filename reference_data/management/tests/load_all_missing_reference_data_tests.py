import mock

from django.core.management import call_command
from django.test import TestCase

from reference_data.management.commands.update_mgi import MGIReferenceDataHandler

class LoadAllMissingReferenceDataTest(TestCase):
    databases = '__all__'
    fixtures = []

    def setUp(self):
        patcher = mock.patch('reference_data.management.commands.utils.update_utils.ReferenceDataHandler.__init__', lambda *args: None)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_all_reference_data.update_gencode')
        self.mock_update_gencode = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_all_reference_data.update_hpo')
        self.mock_update_hpo = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_all_reference_data.update_records')
        self.mock_update_records = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_all_reference_data.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)

    def test_load_all_missing_reference_data_command(self):
        call_command('load_all_missing_reference_data')

        calls = [
            mock.call(39, reset=True),
            mock.call(31),
            mock.call(29),
            mock.call(28),
            mock.call(27),
            mock.call(19),
        ]
        self.mock_update_gencode.assert_has_calls(calls)

        self.assertEqual(self.mock_update_records.call_count, 7)
        self.assertListEqual([
            'CachedOmimReferenceDataHandler',
            'DbNSFPReferenceDataHandler',
            'GeneConstraintReferenceDataHandler',
            'CNSensitivityReferenceDataHandler',
            'PrimateAIReferenceDataHandler',
            'GenCCReferenceDataHandler',
            'ClinGenReferenceDataHandler',
        ], [type(call.args[0]).__name__ for call in self.mock_update_records.mock_calls])

        self.mock_update_hpo.assert_called_with()

        calls = [
            mock.call('Done'),
            mock.call('Updated: gencode, omim, dbnsfp_gene, gene_constraint, gene_cn_sensitivity, primate_ai, gencc, clingen, hpo'),
            mock.call('Failed to Update: mgi, refseq'),
        ]
        self.mock_logger.info.assert_has_calls(calls)

        calls = [
            mock.call("unable to update mgi: dbNSFPGene table is empty. Run './manage.py update_dbnsfp_gene' before running this command."),
            mock.call("unable to update refseq: TranscriptInfo table is empty. Run './manage.py update_gencode' before running this command."),
        ]
        self.mock_logger.error.assert_has_calls(calls)

    def test_load_all_missing_reference_data_data_loaded(self):
        # Intialize DB
        call_command('loaddata', 'reference_data', '--database=reference_data')

        call_command('load_all_missing_reference_data')

        self.mock_update_gencode.assert_not_called()
        self.mock_update_hpo.assert_not_called()

        self.assertEqual(self.mock_update_records.call_count, 1)
        self.assertIsInstance(self.mock_update_records.mock_calls[0].args[0], MGIReferenceDataHandler)

        self.mock_logger.info.assert_has_calls([
            mock.call('Done'),
            mock.call('Updated: mgi'),
        ])
        self.mock_logger.error.assert_not_called()
