# -*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.urls.base import reverse

from seqr.models import Sample, RnaSeqTpm, RnaSeqOutlier
from seqr.views.utils.test_utils import AuthenticationTestCase
from seqr.views.apis.summary_data_api import rna_seq_expression

RNA_FILE_ID = 'all_tissue_tpms.tsv.gz'
MAPPING_FILE_ID = 'mapping.tsv'
EXISTING_SAMPLE_GUID = 'S000150_na19675_d2'

class LoadRnaSeqTest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    @mock.patch('seqr.views.utils.dataset_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.management.commands.load_rna_seq_tpm.logger')
    @mock.patch('seqr.management.commands.load_rna_seq_tpm.open')
    @mock.patch('seqr.views.utils.dataset_utils.gzip.open')
    def test_command(self, mock_gzip_open, mock_open, mock_logger):
        mock_gzip_file = mock_gzip_open.return_value.__enter__.return_value
        mock_gzip_file.__next__.return_value = ''
        mock_gzip_file.__iter__.return_value = [
            'ENSG00000240361\t12.6\t3.01\t13.0\t3.1\n',
            'ENSG00000233750\t1.04\t6.04\t5.31\t7.8\n',
            'ENSG00000233750\t0.0\t0.0\t0.0\t0.0\n',
        ]

        mock_open.return_value.__enter__.return_value.__iter__.return_value = ['sample_id']
        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_tpm', RNA_FILE_ID, MAPPING_FILE_ID)
        self.assertEqual(str(e.exception), 'Invalid mapping file: missing column(s) imputed tissue, indiv (seqr)')

        mock_open.return_value.__enter__.return_value.__iter__.return_value = [
            'sample_id\tindiv (seqr)\timputed tissue',
            'NA19675_D2\tNA19675_1\tmuscle',
            'NA19678_D1\tNA19678\twhole_blood',
            'NA19678_D2\tNA19678\tfibroblasts',
            'NA19679\tNA19679_1\tmuscle',
            'NA19676\t\t',
        ]
        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_tpm', RNA_FILE_ID, MAPPING_FILE_ID)
        self.assertEqual(str(e.exception), 'Invalid file: missing column gene_id')

        mock_gzip_file.__next__.return_value = 'gene_id\tNA19675_D2\tNA19678_D1\tNA19678_D2\tNA19676\tNA19679\tGTEX-001\n'
        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_tpm', RNA_FILE_ID, MAPPING_FILE_ID)
        self.assertEqual(str(e.exception), 'Unable to load data for the following individuals with multiple samples: NA19678 (NA19678_D1, NA19678_D2)')

        mock_gzip_file.__next__.return_value = 'gene_id\tNA19675_D2\tNA19678_D1\tNA19676\tNA19679\tGTEX-001\n'
        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_tpm', RNA_FILE_ID, MAPPING_FILE_ID)
        self.assertEqual(str(e.exception), 'Unable to load data for the following samples with no tissue type: NA19676')

        mock_gzip_file.__next__.return_value = 'gene_id\tNA19675_D2\tNA19678_D1\tNA19679\tGTEX-001\n'
        with self.assertRaises(ValueError) as e:
            call_command('load_rna_seq_tpm', RNA_FILE_ID, MAPPING_FILE_ID)
        self.assertEqual(str(e.exception), 'Unable to find matches for the following samples: NA19679')

        call_command('load_rna_seq_tpm', RNA_FILE_ID, MAPPING_FILE_ID, '--ignore-extra-samples')

        # Existing outlier data should be unchanged
        self.assertEqual(RnaSeqOutlier.objects.count(), 3)

        # Test database models
        existing_sample = Sample.objects.get(individual_id=1, sample_type='RNA')
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
        self.assertEqual(models.count(), 4)
        self.assertSetEqual({model.sample for model in models}, {existing_sample, new_sample})
        self.assertEqual(models.get(sample=existing_sample, gene_id='ENSG00000240361').tpm, 12.6)
        self.assertEqual(models.get(sample=new_sample, gene_id='ENSG00000233750').tpm, 6.04)

        mock_logger.info.assert_has_calls([
            mock.call('create 2 RnaSeqTpm for NA19675_D2'),
            mock.call('create 2 RnaSeqTpm for NA19678_D1'),
        ])
        mock_logger.warning.assert_not_called()

        # Test TPM expression API
        url = reverse(rna_seq_expression, args=['ENSG00000233750', 'F,M,WB'])
        self.check_require_login(url)
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'F': [],
            'M': [1.04],
            'WB': [6.04],
        })

        # Test fails on mismatched tissue
        mock_open.return_value.__enter__.return_value.__iter__.return_value[2] = 'NA19678_D1\tNA19678\tfibroblasts'
        call_command('load_rna_seq_tpm', 'new_file.tsv.gz', MAPPING_FILE_ID, '--ignore-extra-samples')
        mock_logger.warning.assert_called_with('Skipped data loading for the following 1 samples due to mismatched tissue type: NA19678_D1 (fibroblasts to whole_blood)')


