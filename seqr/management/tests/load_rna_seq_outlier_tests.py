# -*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase

from seqr.models import Sample, RnaSeqOutlier

RNA_FILE_ID = 'tmp_-_2021-03-01T00:00:00_-_test_data_manager_-_new_muscle_samples.tsv.gz'
EXISTING_SAMPLE_GUID = 'S000150_na19675_d2'

class LoadRnaSeqTest(TestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data']

    @mock.patch('seqr.management.commands.load_rna_seq_outlier.logger.info')
    @mock.patch('seqr.management.commands.load_rna_seq_outlier.open')
    @mock.patch('seqr.utils.file_utils.gzip.open')
    def test_command(self, mock_gzip_open, mock_open, mock_logger):
        mock_gzip_file = mock_gzip_open.return_value.__enter__.return_value
        mock_gzip_file.__iter__.return_value = ['invalid\theader']

        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_outlier', RNA_FILE_ID)
        self.assertEqual(str(e.exception), 'Invalid file: missing column(s): geneID, pValue, padjust, project, sampleID, zScore')

        mock_gzip_file.__iter__.return_value = [
            'sampleID\tproject\tgeneID\tdetail\tpValue\tpadjust\tzScore\n',
            'NA19675_D2\t1kg project nåme with uniçøde\tENSG00000240361\tdetail1\t0.01\t0.13\t-3.1\n',
            'NA19675_D2\t1kg project nåme with uniçøde\tENSG00000240361\tdetail2\t0.01\t0.13\t-3.1\n',
            'NA19675_D2\t1kg project nåme with uniçøde\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8\n',
            'NA19675_D3\t1kg project nåme with uniçøde\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8\n',
            'NA19675_D4\t1kg project nåme with uniçøde\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8\n',
        ]
        mock_open.return_value.__enter__.return_value.__iter__.return_value = ['NA19675_D4\tNA19678']

        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_outlier', RNA_FILE_ID)
        self.assertEqual(str(e.exception), 'Unable to find matches for the following samples: NA19675_D3, NA19675_D4')

        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_outlier', RNA_FILE_ID, '--mapping-file', 'map.tsv')
        self.assertEqual(str(e.exception), 'Unable to find matches for the following samples: NA19675_D3')

        call_command('load_rna_seq_outlier', RNA_FILE_ID, '--ignore-extra-samples')

        rna_samples = Sample.objects.filter(individual_id=1, sample_id='NA19675_D2', sample_type='RNA')
        self.assertEqual(len(rna_samples), 2)
        sample = rna_samples.first()
        self.assertEqual(sample.guid, EXISTING_SAMPLE_GUID)
        self.assertTrue(sample.is_active)
        self.assertIsNone(sample.elasticsearch_index)
        self.assertEqual(sample.data_source, 'new_muscle_samples.tsv.gz')

        models = RnaSeqOutlier.objects.all()
        self.assertEqual(models.count(), 2)
        self.assertSetEqual({model.sample for model in models}, {sample})
        self.assertListEqual(list(models.values_list('gene_id', 'p_adjust', 'p_value', 'z_score')), [
            ('ENSG00000240361', 0.13, 0.01, -3.1), ('ENSG00000233750', 0.0000057, 0.064, 7.8),
        ])
        mock_logger.assert_called_with('create 2 RnaSeqOutliers for NA19675_D2')
