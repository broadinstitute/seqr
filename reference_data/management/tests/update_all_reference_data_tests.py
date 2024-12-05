import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from reference_data.management.commands.utils.update_utils import ReferenceDataHandler
from reference_data.management.commands.update_dbnsfp_gene import DbNSFPReferenceDataHandler
from reference_data.management.commands.update_gene_constraint import GeneConstraintReferenceDataHandler
from reference_data.management.commands.update_gene_cn_sensitivity import CNSensitivityReferenceDataHandler
from reference_data.management.commands.update_gencc import GenCCReferenceDataHandler
from reference_data.management.commands.update_clingen import ClinGenReferenceDataHandler
from reference_data.management.commands.update_refseq import RefseqReferenceDataHandler
from reference_data.models import GeneInfo


def omim_exception(omim_key):
    raise Exception('Omim exception, key: '+omim_key)


def primate_ai_exception():
    raise Exception('Primate_AI failed')


def mgi_exception():
    raise Exception('MGI failed')

SKIP_ARGS = [
    '--skip-gencode', '--skip-dbnsfp-gene', '--skip-gene-constraint', '--skip-primate-ai', '--skip-mgi', '--skip-hpo',
    '--skip-gene-cn-sensitivity', '--skip-gencc', '--skip-clingen', '--skip-refseq',
]

class UpdateAllReferenceDataTest(TestCase):
    databases = '__all__'
    fixtures = ['users', 'reference_data']

    def setUp(self):
        self.mock_handlers = []
        def _mock_init_handler(_self, **kwargs):
            self.mock_handlers.append(type(_self))
            return None
        patcher = mock.patch.object(ReferenceDataHandler, '__init__', _mock_init_handler)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(RefseqReferenceDataHandler, '__init__', _mock_init_handler)
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('reference_data.management.commands.update_mgi.MGIReferenceDataHandler')
        patcher.start().side_effect = mgi_exception
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_primate_ai.PrimateAIReferenceDataHandler')
        patcher.start().side_effect = primate_ai_exception
        self.addCleanup(patcher.stop)

        patcher = mock.patch('reference_data.management.commands.update_all_reference_data.OmimReferenceDataHandler')
        self.mock_omim = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_all_reference_data.CachedOmimReferenceDataHandler')
        self.mock_cached_omim = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_all_reference_data.update_gencode')
        self.mock_update_gencode = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_all_reference_data.update_hpo')
        self.mock_update_hpo = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(ReferenceDataHandler, 'update_records')
        self.mock_update_records = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.management.commands.update_all_reference_data.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)

    def test_update_all_reference_data_command(self):

        # Test missing required arguments
        with self.assertRaises(CommandError) as err:
            call_command('update_all_reference_data')
        self.assertEqual(str(err.exception), 'Error: one of the arguments --omim-key --use-cached-omim --skip-omim is required')

        # Test update is skipped when data is already loaded
        self.mock_update_gencode.assert_not_called()
        self.mock_omim.assert_not_called()
        self.mock_cached_omim.assert_not_called()
        self.mock_update_records.assert_not_called()
        self.mock_update_hpo.assert_not_called()

        # Test update all gencode, no skips, fail primate_ai and mgi
        GeneInfo.objects.all().delete()
        call_command('update_all_reference_data', '--omim-key=test_key')

        calls = [
            mock.call(39, reset=True),
            mock.call(31),
            mock.call(29),
            mock.call(28),
            mock.call(27),
            mock.call(19),
        ]
        self.mock_update_gencode.assert_has_calls(calls)

        self.mock_omim.assert_called_with('test_key')
        self.mock_cached_omim.assert_not_called()
        self.mock_omim.return_value.update_records.assert_called_with()
        self.assertEqual(self.mock_update_records.call_count, 6)
        self.assertListEqual(self.mock_handlers, [
            DbNSFPReferenceDataHandler,
            GeneConstraintReferenceDataHandler,
            CNSensitivityReferenceDataHandler,
            GenCCReferenceDataHandler,
            ClinGenReferenceDataHandler,
            RefseqReferenceDataHandler,
        ])

        self.mock_update_hpo.assert_called_with()

        calls = [
            mock.call('Done'),
            mock.call('Updated: gencode, omim, dbnsfp_gene, gene_constraint, gene_cn_sensitivity, gencc, clingen, refseq, hpo'),
            mock.call('Failed to Update: primate_ai, mgi')
        ]
        self.mock_logger.info.assert_has_calls(calls)

        calls = [
            mock.call('unable to update primate_ai: Primate_AI failed'),
            mock.call('unable to update mgi: MGI failed')
        ]
        self.mock_logger.error.assert_has_calls(calls)

    def test_skip_all_update_reference_data_command(self):
        call_command(
            'update_all_reference_data', '--skip-omim', *SKIP_ARGS)

        self.mock_update_gencode.assert_not_called()
        self.mock_omim.assert_not_called()
        self.mock_cached_omim.assert_not_called()
        self.mock_update_records.assert_not_called()
        self.mock_update_hpo.assert_not_called()
        self.mock_logger.info.assert_called_with("Done")

    def test_cached_omim_update_reference_data_command(self):
        call_command(
            'update_all_reference_data', '--use-cached-omim', *SKIP_ARGS)

        self.mock_cached_omim.assert_called_with()
        self.mock_cached_omim.return_value.update_records.assert_called_with()
        self.mock_update_records.assert_not_called()

        self.mock_omim.assert_not_called()
        self.mock_update_gencode.assert_not_called()
        self.mock_update_hpo.assert_not_called()

        calls = [
            mock.call('Done'),
            mock.call('Updated: omim')
        ]
        self.mock_logger.info.assert_has_calls(calls)

    def test_omim_exception(self):
        self.mock_omim.side_effect = omim_exception
        call_command('update_all_reference_data', '--omim=test_key', *SKIP_ARGS)

        self.mock_update_gencode.assert_not_called()
        self.mock_omim.assert_called_with('test_key')
        self.mock_update_records.assert_not_called()
        self.mock_update_hpo.assert_not_called()

        calls = [
            mock.call('Done'),
            mock.call('Failed to Update: omim')
        ]
        self.mock_logger.info.assert_has_calls(calls)

        self.mock_logger.error.assert_called_with("unable to update omim: Omim exception, key: test_key")

