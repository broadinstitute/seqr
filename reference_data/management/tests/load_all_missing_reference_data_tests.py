import mock

from django.core.management import call_command
from django.test import TestCase


def refseq_exception():
    raise Exception('Refseq failed')


def mgi_exception():
    raise Exception('MGI failed')

class LoadAllMissingReferenceDataTest(TestCase):
    databases = '__all__'
    fixtures = []

    def setUp(self):
        patcher = mock.patch('reference_data.management.commands.utils.update_utils.ReferenceDataHandler.__init__', lambda *args: None)
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('reference_data.management.commands.update_mgi.MGIReferenceDataHandler.__init__')
        patcher.start().side_effect = mgi_exception
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_refseq.RefseqReferenceDataHandler.__init__')
        patcher.start().side_effect = refseq_exception
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
            mock.call('unable to update mgi: MGI failed'),
            mock.call('unable to update refseq: Refseq failed'),
        ]
        self.mock_logger.error.assert_has_calls(calls)
