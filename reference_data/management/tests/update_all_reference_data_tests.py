import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from reference_data.models import GeneInfo, Omim, dbNSFPGene, GeneConstraint, GeneCopyNumberSensitivity, GenCC, ClinGen, \
    RefseqTranscript, HumanPhenotypeOntology, MGI, PrimateAI, LoadableModel


def primate_ai_exception():
    raise Exception('Primate_AI failed')


def mgi_exception():
    raise Exception('MGI failed')

SKIP_ARGS = [
    '--skip-gencode', '--skip-dbnsfp-gene', '--skip-gene-constraint', '--skip-primate-ai', '--skip-mgi', '--skip-hpo',
    '--skip-gene-cn-sensitivity', '--skip-gencc', '--skip-clingen', '--skip-refseq',
]

class BaseUpdateAllReferenceDataTest(object):

    def set_up(self):
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
        patcher = mock.patch('reference_data.models.LoadableModel._get_file_last_modified')
        patcher.start().return_value = 'Thu, 20 Mar 2025 20:52:24 GMT'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.models.ClinGen.get_current_version')
        patcher.start().return_value = '2025-02-05'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('reference_data.models.HumanPhenotypeOntology.get_current_version')
        patcher.start().return_value = '2025-03-03'
        self.addCleanup(patcher.stop)


class NewDbUpdateAllReferenceDataTest(BaseUpdateAllReferenceDataTest, TestCase):
    databases = '__all__'

    def setUp(self):
        super().set_up()

    def test_empty_db_update_all_reference_data_command(self):
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


class UpdateAllReferenceDataTest(BaseUpdateAllReferenceDataTest, TestCase):
    databases = '__all__'
    fixtures = ['users', 'reference_data']

    def setUp(self):
        super().set_up()

    def test_all_loaded_update_reference_data_command(self):
        call_command('update_all_reference_data')

        self.mock_update_gencode.assert_not_called()
        self.assertListEqual(self.mock_update_calls, [])
        self.mock_logger.info.assert_called_with("Done")
