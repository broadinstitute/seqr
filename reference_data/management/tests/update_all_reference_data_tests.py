import mock

from django.core.management import call_command
from django.core.management.base import CommandError

from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase
from reference_data.models import Omim, dbNSFPGene, GeneConstraint, GeneCopyNumberSensitivity, GenCC, ClinGen, \
    RefseqTranscript, HumanPhenotypeOntology, MGI, PrimateAI, GeneShet, LoadableModel, DataVersions


def primate_ai_exception():
    raise Exception('Primate_AI failed')


def mgi_exception():
    raise Exception('MGI failed')

SKIP_ARGS = [
    '--skip-gencode', '--skip-dbnsfp-gene', '--skip-gene-constraint', '--skip-primate-ai', '--skip-mgi', '--skip-hpo',
    '--skip-gene-cn-sensitivity', '--skip-gencc', '--skip-clingen', '--skip-refseq',
]

class BaseUpdateAllReferenceDataTest(ReferenceDataCommandTestCase):

    def setUp(self):
        super().setUp()

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
        patcher = mock.patch('seqr.utils.communication_utils._post_to_slack')
        self.mock_slack = patcher.start()
        self.addCleanup(patcher.stop)


class NewDbUpdateAllReferenceDataTest(BaseUpdateAllReferenceDataTest):
    fixtures = []

    def test_empty_db_update_all_reference_data_command(self):
        with self.assertRaises(CommandError) as e:
            call_command('update_all_reference_data', '--omim-key=test_key')

        calls = [
            mock.call('39', set(), set(), gene_symbol_change_dir=None),
            mock.call('31', set(), set(), gene_symbol_change_dir=None),
            mock.call('29', set(), set(), gene_symbol_change_dir=None),
            mock.call('28', set(), set(), gene_symbol_change_dir=None),
            mock.call('27', set(), set(), gene_symbol_change_dir=None),
            mock.call('19', set(), set(), gene_symbol_change_dir=None),
        ]
        self.mock_update_gencode.assert_has_calls(calls)

        kwargs = {'gene_ids_to_gene': {}, 'gene_symbols_to_gene': {}}
        gene_kwargs = {**kwargs, 'skipped_genes': {None: 0}}
        self.assertListEqual(self.mock_update_calls, [
            (RefseqTranscript, {'transcript_id_map': {}, 'skipped_transcripts': {None: 0}}),
            (Omim, {**kwargs, 'omim_key': 'test_key'}),
            (dbNSFPGene, gene_kwargs),
            (GeneConstraint, gene_kwargs),
            (GeneCopyNumberSensitivity, gene_kwargs),
            (PrimateAI, gene_kwargs),
            (MGI, {**gene_kwargs, 'entrez_id_to_gene': {}}),
            (GenCC, gene_kwargs),
            (ClinGen, gene_kwargs),
            (GeneShet, gene_kwargs),
            (HumanPhenotypeOntology, kwargs),
        ])

        self.mock_slack.assert_not_called()
        calls = [
            mock.call('Done'),
            mock.call('Updated: GeneInfo, Omim, dbNSFPGene, GeneConstraint, GeneCopyNumberSensitivity, GenCC, ClinGen, GeneShet, HumanPhenotypeOntology'),
        ]
        self.mock_logger.info.assert_has_calls(calls)

        calls = [
            mock.call('unable to update PrimateAI: Primate_AI failed'),
            mock.call('unable to update MGI: MGI failed')
        ]
        self.mock_logger.error.assert_has_calls(calls)

        self.assertEqual(str(e.exception),'Failed to Update: PrimateAI, MGI')

        self.assertListEqual(sorted(DataVersions.objects.values_list('data_model_name', 'version')), [
            ('ClinGen', '2025-02-05'),
            ('GenCC', 'Thu, 20 Mar 2025 20:52:24 GMT'),
            ('GeneConstraint', 'gnomad.v2.1.1.lof_metrics.by_gene'),
            ('GeneCopyNumberSensitivity', 'Collins_rCNV_2022'),
            ('GeneInfo', '39'),
            ('GeneShet', '7939768'),
            ('HumanPhenotypeOntology', '2025-03-03'),
            ('Omim', 'Thu, 20 Mar 2025 20:52:24 GMT'),
            ('dbNSFPGene', 'dbNSFP4.0_gene'),
        ])


class UpdateAllReferenceDataTest(BaseUpdateAllReferenceDataTest):

    def test_all_loaded_update_reference_data_command(self):
        call_command('update_all_reference_data')

        self.mock_update_gencode.assert_not_called()
        self.assertListEqual(self.mock_update_calls, [])
        self.mock_logger.info.assert_called_with("Done")
        self.mock_slack.assert_not_called()

    def test_partial_update_reference_data_command(self):
        self.mock_get_file_last_modified.return_value = 'Sat, 22 Mar 2025 09:21:17 GMT'
        dbnsfp_version = DataVersions.objects.get(data_model_name='dbNSFPGene')
        dbnsfp_version.version = 'dbNSFP3.2_gene'
        dbnsfp_version.save()

        call_command('update_all_reference_data')

        self.mock_update_gencode.assert_not_called()
        kwargs = {'gene_ids_to_gene': mock.ANY, 'gene_symbols_to_gene': mock.ANY}
        gene_kwargs = {**kwargs, 'skipped_genes': {None: 0}}
        self.assertListEqual(self.mock_update_calls, [
            (Omim, kwargs),
            (dbNSFPGene, gene_kwargs),
            (GenCC, gene_kwargs),
        ])
        self.assertEqual(len(self.mock_update_calls[0][1]['gene_ids_to_gene']), 51)
        self.assertEqual(len(self.mock_update_calls[0][1]['gene_symbols_to_gene']), 50)

        self.mock_logger.info.assert_has_calls([
            mock.call('Done'),
            mock.call('Updated: Omim, dbNSFPGene, GenCC'),
        ])
        self.mock_logger.error.assert_not_called()
        self.mock_slack.assert_has_calls([mock.call('seqr-data-loading', message) for message in [
            'Updated Omim reference data from version "Thu, 20 Mar 2025 20:52:24 GMT" to version "Sat, 22 Mar 2025 09:21:17 GMT"',
            'Updated dbNSFPGene reference data from version "dbNSFP3.2_gene" to version "dbNSFP4.0_gene"',
            'Updated GenCC reference data from version "Thu, 20 Mar 2025 20:52:24 GMT" to version "Sat, 22 Mar 2025 09:21:17 GMT"',
        ]])

        self.assertEqual(DataVersions.objects.get(data_model_name='Omim').version, 'Sat, 22 Mar 2025 09:21:17 GMT')
        self.assertEqual(DataVersions.objects.get(data_model_name='dbNSFPGene').version, 'dbNSFP4.0_gene')
        self.assertEqual(DataVersions.objects.get(data_model_name='GenCC').version, 'Sat, 22 Mar 2025 09:21:17 GMT')
