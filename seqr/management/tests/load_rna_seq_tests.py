# -*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.core.management.base import CommandError

from seqr.models import RnaSample, RnaSeqTpm, RnaSeqOutlier
from seqr.utils.middleware import ErrorsWarningsException
from seqr.views.utils.test_utils import AuthenticationTestCase

RNA_FILE_ID = 'all_tissue_tpms.tsv.gz'
MAPPING_FILE_ID = 'mapping.tsv'


class LoadRnaSeqTest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        patcher = mock.patch('seqr.utils.file_utils.gzip.open')
        mock_gzip_open = patcher.start()
        self.mock_gzip_file_iter = mock_gzip_open.return_value.__enter__.return_value.__iter__
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.management.commands.load_rna_seq.open')
        self.mock_open = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.management.commands.load_rna_seq.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)

    def _test_invalid_calls(self, data_type, expected_columns, file_data, unmatched_samples, additional_errors=None):
        self.mock_gzip_file_iter.return_value = ['invalid\theader']

        with self.assertRaises(CommandError) as e:
            call_command('load_rna_seq', 'not_a_type', RNA_FILE_ID)
        self.assertEqual(
            str(e.exception),
            "Error: argument data_type: invalid choice: 'not_a_type' (choose from 'outlier', 'splice_outlier', 'tpm')")

        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq', data_type, RNA_FILE_ID)
        self.assertEqual(str(e.exception), f'Invalid file: missing column(s): {expected_columns}')

        self.mock_gzip_file_iter.return_value = file_data
        with self.assertRaises(ErrorsWarningsException) as e:
            call_command('load_rna_seq', data_type, RNA_FILE_ID)
        self.assertListEqual(e.exception.errors, (additional_errors or []) + [
            f'Unable to find matches for the following samples: {unmatched_samples}',
        ])

    def _assert_expected_existing_sample(self, data_type, data_source, guid, tissue_type='M'):
        existing_sample = RnaSample.objects.get(individual_id=1, data_type=data_type, data_source=data_source, tissue_type=tissue_type)
        self.assertEqual(existing_sample.guid, guid)
        self.assertTrue(existing_sample.is_active)
        return existing_sample

    @mock.patch('seqr.views.utils.dataset_utils.logger')
    def test_tpm(self, mock_utils_logger):
        self._test_invalid_calls(
            'tpm',
            expected_columns='TPM, gene_id, project, sample_id, tissue',
            file_data=[
                'sample_id\tproject\tindividual_id\tgene_id\tTPM\ttissue\n',
                'NA19675_D2\t1kg project nåme with uniçøde\t\tENSG00000240361\t12.6\t\n',
                'NA19675_D2\t1kg project nåme with uniçøde\t\tENSG00000233750\t1.26\t\n',
                'NA19678_D1\t1kg project nåme with uniçøde\t\tENSG00000233750\t 6.04\twhole_blood\n',
                'NA19677\t1kg project nåme with uniçøde\t\tENSG00000233750\t5.31\tmuscle\n',
                'NA19678\tTest Reprocessed Project\t\tENSG00000240361\t0.2\twhole_blood\n',
                'NA20870\tTest Reprocessed Project\t\tENSG00000240361\t0.2\twhole_blood\n',
                'NA20870\tTest Reprocessed Project\t\tENSG00000240361\t0.7\twhole_blood\n',
            ],
            unmatched_samples='NA19677 (1kg project nåme with uniçøde), NA19678 (Test Reprocessed Project), NA19678_D1 (1kg project nåme with uniçøde)',
            additional_errors=['Samples missing required "tissue": NA19675_D2'],
        )

        self.mock_gzip_file_iter.return_value = [
            self.mock_gzip_file_iter.return_value[0],
            'NA19678_D1\t1kg project nåme with uniçøde\tNA19678\tENSG00000233750\t 6.04\twhole_blood\n',
        ] + self.mock_gzip_file_iter.return_value[3:]
        call_command('load_rna_seq', 'tpm', RNA_FILE_ID, '--ignore-extra-samples')

        # Existing outlier data should be unchanged
        self.assertEqual(RnaSeqOutlier.objects.count(), 3)

        # Test database models
        existing_sample = self._assert_expected_existing_sample('T', 'muscle_samples.tsv.gz', 'RS000162_T_na19675_d2')
        existing_rna_samples = RnaSample.objects.filter(rnaseqtpm__isnull=False)

        new_sample = RnaSample.objects.get(individual_id=2)
        self.assertEqual(new_sample.data_type, 'T')
        self.assertTrue(new_sample.is_active)
        self.assertEqual(new_sample.data_source, 'all_tissue_tpms.tsv.gz')
        self.assertEqual(new_sample.tissue_type, 'WB')

        models = RnaSeqTpm.objects.all()
        self.assertEqual(models.count(), 5)
        self.assertSetEqual({model.sample for model in models}, set(existing_rna_samples))
        self.assertEqual(models.filter(sample=existing_sample, gene_id='ENSG00000240361').count(), 0)
        self.assertEqual(models.get(sample=new_sample, gene_id='ENSG00000233750').tpm, 6.04)

        self.mock_logger.info.assert_has_calls([
            mock.call('create 1 RnaSeqTpm for NA19678'),
            mock.call('Error in T_NA20870: mismatched entries for ENSG00000240361'),
            mock.call('DONE'),
        ])
        mock_utils_logger.warning.assert_has_calls([
            mock.call('Skipped loading for the following 2 unmatched samples: NA19677 (1kg project nåme with uniçøde), NA19678 (Test Reprocessed Project)', None),
        ])

        # Test a new sample created for a mismatched tissue and a row with 0.0 tpm
        self.mock_gzip_file_iter.return_value[1] = 'NA19678_D1\t1kg project nåme with uniçøde\tNA19678\tENSG00000233750\t0.0\tfibroblasts\n'
        call_command('load_rna_seq', 'tpm', 'new_file.tsv.gz', '--ignore-extra-samples')
        models = RnaSeqTpm.objects.select_related('sample').filter(sample__individual_id=2)
        self.assertEqual(models.count(), 2)
        self.assertSetEqual(set(models.values_list('sample__tissue_type', flat=True)), {'F', 'WB'})
        self.assertEqual(models.get(gene_id='ENSG00000233750', sample__tissue_type='F').tpm, 0.0)
        self.assertEqual(models.values('sample').distinct().count(), 2)
        self.mock_logger.info.assert_has_calls([
            mock.call('create 1 RnaSeqTpm for NA19678'),
            mock.call('Error in T_NA20870: mismatched entries for ENSG00000240361'),
            mock.call('DONE'),
        ])

    def test_outlier(self):
        self._test_invalid_calls(
            'outlier',
            expected_columns='geneID, pValue, padjust, project, sampleID, tissue, zScore',
            file_data=[
                'sampleID\tproject\tgeneID\tdetail\tpValue\tpadjust\tzScore\ttissue\n',
                'NA19675_1\t1kg project nåme with uniçøde\tENSG00000240361\tdetail1\t0.01\t0.13\t-3.1\tmuscle\n',
                'NA19675_1\t1kg project nåme with uniçøde\tENSG00000240361\tdetail2\t0.01\t0.13\t-3.1\tmuscle\n',
                'NA19675_1\t1kg project nåme with uniçøde\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8\tmuscle\n',
                'NA19675_D3\t1kg project nåme with uniçøde\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8\tmuscle\n',
                'NA19675_D4\t1kg project nåme with uniçøde\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8\tmuscle\n',
            ],
            unmatched_samples='NA19675_D3 (1kg project nåme with uniçøde), NA19675_D4 (1kg project nåme with uniçøde)',
        )

        self.mock_open.return_value.__enter__.return_value.__iter__.return_value = ['NA19675_D4\tNA19678']
        with self.assertRaises(ErrorsWarningsException) as e:
            call_command('load_rna_seq', 'outlier', RNA_FILE_ID, '--mapping-file', 'map.tsv')
        self.assertEqual(e.exception.errors, ['Unable to find matches for the following samples: NA19675_D3 (1kg project nåme with uniçøde)'])

        call_command('load_rna_seq', 'outlier', RNA_FILE_ID, '--ignore-extra-samples')

        sample = self._assert_expected_existing_sample('E', 'all_tissue_tpms.tsv.gz', guid=mock.ANY)
        self.assertFalse(RnaSample.objects.get(guid='RS000172_E_na19675_d2').is_active)

        models = RnaSeqOutlier.objects.all()
        self.assertEqual(models.count(), 2)
        self.assertSetEqual({model.sample for model in models}, {sample})
        self.assertListEqual(list(models.values_list('gene_id', 'p_adjust', 'p_value', 'z_score')), [
            ('ENSG00000240361', 0.13, 0.01, -3.1), ('ENSG00000233750', 0.0000057, 0.064, 7.8),
        ])
        self.mock_logger.info.assert_has_calls([
            mock.call('create 2 RnaSeqOutlier for NA19675_1'),
            mock.call('DONE'),
        ])
