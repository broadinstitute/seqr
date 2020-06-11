from __future__ import unicode_literals

import mock

import os
import tempfile
import shutil

from django.core.management import call_command
from django.test import TestCase

from reference_data.models import MGI, dbNSFPGene
from django.core.management.base import CommandError

MGI_DATA = [
    'A1BG	  1	11167	yes	A1bg	  MGI:2152878		\n',
    'A1CF	  29974	16363	yes	A1cf	  MGI:1917115	  MP:0005367 MP:0005370 MP:0005385 MP:0010768 MP:0005369 MP:0005376 MP:0005384 MP:0005378\n',
    'A2M	  2	37248	yes	A2m	  MGI:2449119\n',
    'A3GALT2\xe2	  127550	16326	yes	A3galt2	  MGI:2685279\n',
]


class UpdateMgiTest(TestCase):
    fixtures = ['users', 'reference_data']
    multi_db = True

    def setUp(self):
        # Create a temporary directory and a test data file
        self.test_dir = tempfile.mkdtemp()
        self.temp_file_path = os.path.join(self.test_dir, 'HMD_HumanPhenotype.rpt')
        with open(self.temp_file_path, 'wb') as f:
            f.write(''.join(MGI_DATA).encode('utf-8'))

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        shutil.rmtree(self.test_dir)

    @mock.patch('reference_data.management.commands.utils.update_utils.logger')
    @mock.patch('reference_data.management.commands.utils.update_utils.download_file')
    def test_update_mgi_command(self, mock_download, mock_logger):

        mock_download.return_value = self.temp_file_path

        # test without a file_path parameter
        call_command('update_mgi')

        mock_download.assert_called_with('http://www.informatics.jax.org/downloads/reports/HMD_HumanPhenotype.rpt')

        calls = [
            mock.call('Deleting 0 existing MGI records'),
            mock.call('Parsing file'),
            mock.call('Creating 2 MGI records'),
            mock.call('Done'),
            mock.call('Loaded 2 MGI records from {}. Skipped 2 records with unrecognized genes.'.format(self.temp_file_path)),
            mock.call('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
        ]
        mock_logger.info.assert_has_calls(calls)

        # test with a file_path parameter
        mock_download.reset_mock()
        mock_logger.reset_mock()
        call_command('update_mgi', self.temp_file_path)
        mock_download.assert_not_called()
        calls = [
            mock.call('Deleting 2 existing MGI records'),
            mock.call('Parsing file'),
            mock.call('Creating 2 MGI records'),
            mock.call('Done'),
            mock.call('Loaded 2 MGI records from {}. Skipped 2 records with unrecognized genes.'.format(self.temp_file_path)),
            mock.call('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
        ]
        mock_logger.info.assert_has_calls(calls)

        self.assertEqual(MGI.objects.all().count(), 2)
        record = MGI.objects.get(gene__gene_id = 'ENSG00000223972')
        self.assertEqual(record.marker_id, 'MGI:2152878')

        # Test exception with no dbNSFPGene records
        dbNSFPGene.objects.all().delete()
        with self.assertRaises(CommandError) as ce:
            call_command('update_mgi')
        self.assertEqual(str(ce.exception), 'dbNSFPGene table is empty. Run \'./manage.py update_dbnsfp_gene\' before running this command.')
