import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from reference_data.models import GeneInfo, Omim, dbNSFPGene, GeneConstraint, GeneCopyNumberSensitivity, GenCC, ClinGen, \
    RefseqTranscript, HumanPhenotypeOntology, MGI, PrimateAI, LoadableModel


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
        self.mock_update_calls = []
        def _mock_handler(_cls, **kwargs):
            self.mock_update_calls.append((_cls, kwargs))
            if _cls == MGI:
                mgi_exception()
            elif _cls == PrimateAI:
                primate_ai_exception()
        patcher = mock.patch.object(LoadableModel, 'update_records', new=classmethod(mock.MagicMock(side_effect=_mock_handler)))
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('reference_data.models.GeneInfo.update_records')
        self.mock_update_gencode = patcher.start()
        self.mock_update_gencode.return_value = {}
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
        self.assertListEqual(self.mock_update_calls, [])

        # Test update all gencode, no skips, fail primate_ai and mgi
        GeneInfo.objects.all().delete()
        call_command('update_all_reference_data', '--omim-key=test_key')

        calls = [
            mock.call(39, set(), set()),
            mock.call(31, set(), set()),
            mock.call(29, set(), set()),
            mock.call(28, set(), set()),
            mock.call(27, set(), set()),
            mock.call(19, set(), set()),
        ]
        self.mock_update_gencode.assert_has_calls(calls)

        kwargs = {'gene_ids_to_gene': {}, 'gene_symbols_to_gene': {}}
        gene_kwargs = {**kwargs, 'skipped_genes': {None: 0}}
        self.assertListEqual(self.mock_update_calls, [
            (Omim, {**kwargs, 'omim_key': 'test_key'}),
            (dbNSFPGene, gene_kwargs),
            (GeneConstraint, gene_kwargs),
            (GeneCopyNumberSensitivity, gene_kwargs),
            (PrimateAI, gene_kwargs),
            (MGI, {**gene_kwargs, 'entrez_id_to_gene': {}}),
            (GenCC, gene_kwargs),
            (ClinGen, gene_kwargs),
            (RefseqTranscript, {**kwargs, 'transcript_id_map': {}, 'skipped_transcripts': {None: 0}}),
            (HumanPhenotypeOntology, {}),
        ])

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
        self.assertListEqual(self.mock_update_calls, [])
        self.mock_logger.info.assert_called_with("Done")

    def test_cached_omim_update_reference_data_command(self):
        call_command(
            'update_all_reference_data', '--use-cached-omim', *SKIP_ARGS)

        self.assertListEqual(self.mock_update_calls, [
            (Omim, {'gene_ids_to_gene': mock.ANY, 'gene_symbols_to_gene': mock.ANY}),
        ])
        self.mock_update_gencode.assert_not_called()

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

