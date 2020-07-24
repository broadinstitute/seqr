import mock

import os
import tempfile
import shutil

from django.core.management import call_command
from django.test import TestCase

from reference_data.models import PrimateAI

PRIMATE_AI_DATA = [
    'ucscid	genesymbol	nAllSNPs	pcnt75	pcnt25	nClinvarBenignSNPs	benign_mean	benign_std	nClinvarPathogenicSNPs	pathogenic_mean	pathogenic_std\n',
    'uc021qil.1	CREB3L1	3744	0.748042136	0.432699919	NA	NA	NA	NA	NA	NA\n',
    'uc010nxu.2	OR4F29	2038	0.593389094	0.383666202	NA	NA	NA	NA	NA	NA\n',
    'uc001aal.1	OR4F5	2019	0.569617867	0.335699245	NA	NA	NA	NA	NA	NA\n',
    'uc002ehz.4	MMP2	4389	0.78644371	0.556205034	NA	NA	NA	2	0.842780441	0.114728231\n',
]


class UpdatePrimateAiTest(TestCase):
    fixtures = ['users', 'reference_data']
    multi_db = True

    def setUp(self):
        # Create a temporary directory and a temp data file
        self.test_dir = tempfile.mkdtemp()
        self.temp_file_path = os.path.join(self.test_dir, 'Gene_metrics_clinvar_pcnt.cleaned_v0.2.txt')
        with open(self.temp_file_path, 'w') as f:
            f.write(''.join(PRIMATE_AI_DATA))

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        shutil.rmtree(self.test_dir)

    @mock.patch('reference_data.management.commands.utils.update_utils.logger')
    @mock.patch('reference_data.management.commands.utils.update_utils.download_file')
    def test_update_primate_ai_command(self, mock_download, mock_logger):
        mock_download.return_value = self.temp_file_path

        # test without a file_path parameter
        call_command('update_primate_ai')
        mock_download.assert_called_with('http://storage.googleapis.com/seqr-reference-data/primate_ai/Gene_metrics_clinvar_pcnt.cleaned_v0.2.txt')

        calls = [
            mock.call('Deleting 1 existing PrimateAI records'),
            mock.call('Parsing file'),
            mock.call('Creating 2 PrimateAI records'),
            mock.call('Done'),
            mock.call('Loaded 2 PrimateAI records from {}. Skipped 2 records with unrecognized genes.'.format(self.temp_file_path)),
            mock.call('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
        ]
        mock_logger.info.assert_has_calls(calls)

        # test with a file_path parameter
        mock_download.reset_mock()
        mock_logger.reset_mock()
        call_command('update_primate_ai', self.temp_file_path)
        mock_download.assert_not_called()
        calls = [
            mock.call('Deleting 2 existing PrimateAI records'),
            mock.call('Parsing file'),
            mock.call('Creating 2 PrimateAI records'),
            mock.call('Done'),
            mock.call('Loaded 2 PrimateAI records from {}. Skipped 2 records with unrecognized genes.'.format(self.temp_file_path)),
            mock.call('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
        ]
        mock_logger.info.assert_has_calls(calls)

        self.assertEqual(PrimateAI.objects.all().count(), 2)
        record = PrimateAI.objects.get(gene__gene_id = 'ENSG00000235249')
        self.assertEqual(record.percentile_25, 0.383666202)
        self.assertEqual(record.percentile_75, 0.593389094)
