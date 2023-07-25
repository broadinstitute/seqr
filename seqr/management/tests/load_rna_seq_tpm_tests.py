# -*- coding: utf-8 -*-
import mock

from django.core.management import call_command

from seqr.models import Sample, RnaSeqTpm, RnaSeqOutlier
from seqr.views.utils.test_utils import AuthenticationTestCase

RNA_FILE_ID = 'all_tissue_tpms.tsv.gz'
MAPPING_FILE_ID = 'mapping.tsv'
EXISTING_SAMPLE_GUID = 'S000152_na19675_d2'

class LoadRnaSeqTest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    @mock.patch('seqr.utils.file_utils.gzip.open')
    @mock.patch('seqr.views.utils.dataset_utils.logger')
    @mock.patch('seqr.management.commands.load_rna_seq_tpm.logger')
    @mock.patch('seqr.management.commands.load_rna_seq_tpm.open')
    def test_command(self, mock_open, mock_logger, mock_utils_logger, mock_gzip_open):
        mock_gzip_file = mock_gzip_open.return_value.__enter__.return_value
        mock_gzip_file.__iter__.return_value = [
            '',
            'NA19675_D2\t1kg project nåme with uniçøde\t\tENSG00000240361\t12.6\t\n',
            'NA19678_D1\t1kg project nåme with uniçøde\t\tENSG00000233750\t 6.04\twhole_blood\n',
            'GTEX-001\t1kg project nåme with uniçøde\t\tENSG00000240361\t3.1\tinvalid\n',
            'NA19675_D2\t1kg project nåme with uniçøde\t\tENSG00000233750\t1.04\tmuscle\n',
            'NA19677\t1kg project nåme with uniçøde\t\tENSG00000233750\t5.31\tmuscle\n',
            'GTEX-001\t1kg project nåme with uniçøde\t\tENSG00000233750\t7.8\tmuscle\n',
            'NA19678\tTest Reprocessed Project\t\tENSG00000240361\t0.2\twhole_blood\n',
            'NA19675_D2\t1kg project nåme with uniçøde\t\tENSG00000233750\t1.04\twhole_blood\n',
        ]

        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_tpm', RNA_FILE_ID)
        self.assertEqual(str(e.exception), 'Invalid file: missing column(s): TPM, gene_id, project, sample_id, tissue')

        mock_gzip_file.__iter__.return_value[0] = 'sample_id\tproject\tindividual_id\tgene_id\tTPM\ttissue\n'
        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_tpm', RNA_FILE_ID)
        self.assertEqual(str(e.exception), 'Sample NA19675_D2 has no tissue type')

        mock_gzip_file.__iter__.return_value[1] = 'NA19675_D2\t1kg project nåme with uniçøde\tNA19675_1\tENSG00000240361\t12.6\tmuscle\n'
        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_tpm', RNA_FILE_ID)
        self.assertEqual(str(e.exception), 'Unable to find matches for the following samples: NA19677, NA19678, NA19678_D1')

        mock_gzip_file.__iter__.return_value[2] = 'NA19678_D1\t1kg project nåme with uniçøde\tNA19678\tENSG00000233750\t 6.04\twhole_blood\n'
        call_command('load_rna_seq_tpm', RNA_FILE_ID, '--ignore-extra-samples')

        # Existing outlier data should be unchanged
        self.assertEqual(RnaSeqOutlier.objects.count(), 3)

        # Test database models
        existing_sample = Sample.objects.get(individual_id=1, sample_type='RNA', tissue_type='M')
        existing_rna_samples = Sample.objects.filter(sample_type='RNA', rnaseqtpm__isnull=False)
        self.assertEqual(existing_sample.guid, EXISTING_SAMPLE_GUID)
        self.assertEqual(existing_sample.sample_id, 'NA19675_D2')
        self.assertTrue(existing_sample.is_active)
        self.assertIsNone(existing_sample.elasticsearch_index)
        self.assertEqual(existing_sample.data_source, 'muscle_samples.tsv.gz')
        self.assertEqual(existing_sample.tissue_type, 'M')

        new_sample = Sample.objects.get(individual_id=2, sample_type='RNA')
        self.assertEqual(new_sample.sample_id, 'NA19678_D1')
        self.assertTrue(new_sample.is_active)
        self.assertIsNone(new_sample.elasticsearch_index)
        self.assertEqual(new_sample.data_source, 'all_tissue_tpms.tsv.gz')
        self.assertEqual(new_sample.tissue_type, 'WB')

        models = RnaSeqTpm.objects.all()
        self.assertEqual(models.count(), 5)
        self.assertSetEqual({model.sample for model in models}, set(existing_rna_samples))
        self.assertEqual(models.filter(sample=existing_sample, gene_id='ENSG00000240361').count(), 0)
        self.assertEqual(models.get(sample=new_sample, gene_id='ENSG00000233750').tpm, 6.04)

        mock_logger.info.assert_has_calls([
            mock.call('create 1 RnaSeqTpm for NA19678_D1'),
        ])
        mock_utils_logger.warning.assert_has_calls([
            mock.call('Skipped data loading for the following 1 sample(s) due to mismatched tissue type: NA19675_D2 (muscle, whole_blood)', None),
            mock.call('Skipped loading for the following 2 unmatched samples: NA19677, NA19678', None),
        ])

        # Test a new sample created for a mismatched tissue and a row with 0.0 tpm
        mock_gzip_file.__iter__.return_value[2] = 'NA19678_D1\t1kg project nåme with uniçøde\tNA19678\tENSG00000233750\t0.0\tfibroblasts\n'
        call_command('load_rna_seq_tpm', 'new_file.tsv.gz', '--ignore-extra-samples')
        models = RnaSeqTpm.objects.select_related('sample').filter(sample__sample_id='NA19678_D1')
        self.assertEqual(models.count(), 2)
        self.assertSetEqual(set(models.values_list('sample__tissue_type', flat=True)), {'F', 'WB'})
        self.assertEqual(models.get(gene_id='ENSG00000233750', sample__tissue_type='F').tpm, 0.0)
        self.assertEqual(models.values('sample').distinct().count(), 2)
        mock_logger.info.assert_has_calls([
            mock.call('create 1 RnaSeqTpm for NA19678_D1'),
        ])
