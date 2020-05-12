import mock

import os
import tempfile
import shutil
import responses

from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError

OMIM_DATA = [
    '# Copyright (c) 1966-2020 Johns Hopkins University. Use of this file adheres to the terms specified at https://omim.org/help/agreement.\n',
    '# Chromosome	Genomic Position Start	Genomic Position End	Cyto Location	Computed Cyto Location	MIM Number	Gene Symbols	Gene Name	Approved Symbol	Entrez Gene ID	Ensembl Gene ID	Comments	Phenotypes	Mouse Gene Symbol/ID\n',
    'chr1	0	27600000	1p36		607413	OR4F29	Alzheimer disease neuronal thread protein						\n',
    'chr1	0	27600000	1p36		612367	OR4F5	Alkaline phosphatase, plasma level of, QTL 2		100196914		linkage with rs1780324	{Alkaline phosphatase, plasma level of, QTL 2}, 612367 (2)	\n',
    'chr1	0	123400000	1p		606788	ANON1	Anorexia nervosa, susceptibility to, 1		171514			{Anorexia nervosa, susceptibility to, 1}, 606788 (2)	\n',
    'chr1	0	27600000	1p36		605462	BCC1	Basal cell carcinoma, susceptibility to, 1		100307118		associated with rs7538876	{Basal cell carcinoma, susceptibility to, 1}, 605462 (2)	\n',
]


class UpdateOmimTest(TestCase):
    fixtures = ['users', 'reference_data']
    multi_db = True

    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        shutil.rmtree(self.test_dir)

    @responses.activate
    @mock.patch('reference_data.management.commands.update_omim.os')
    @mock.patch('reference_data.management.commands.utils.update_utils.logger')
    @mock.patch('reference_data.management.commands.utils.update_utils.download_file')
    def test_update_omim_command(self, mock_download, mock_logger, mock_os):
        # Test required argument
        mock_os.environ.get.return_value = ''
        with self.assertRaises(CommandError) as ce:
            call_command('update_omim')
        self.assertEqual(ce.exception.message, 'omim_key is required')

        temp_file_path = os.path.join(self.test_dir, 'genemap2.txt')
        with open(temp_file_path, 'w') as f:
            f.write(u''.join(OMIM_DATA))
        mock_download.return_value = temp_file_path

        # test without a file_path parameter
        call_command('update_omim', '--omim-key=test_key')

        mock_download.assert_called_with('https://data.omim.org/downloads/test_key/genemap2.txt')

        calls = [
            mock.call('Deleting 3 existing Omim records'),
            mock.call('Parsing file'),
            mock.call('Creating 0 Omim records'),
            mock.call('Done'),
            mock.call('Loaded 0 Omim records from {}. Skipped 4 records with unrecognized genes.'.format(temp_file_path)),
            mock.call('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
        ]
        mock_logger.info.assert_has_calls(calls)

        # test with a file_path parameter
        mock_download.reset_mock()
        mock_logger.reset_mock()
        call_command('update_omim', '--omim-key=test_key', temp_file_path)
        mock_download.assert_not_called()
        calls = [
            mock.call('Deleting 2 existing Omim records'),
            mock.call('Parsing file'),
            mock.call('Creating 2 Omim records'),
            mock.call('Done'),
            mock.call('Loaded 2 Omim records from {}. Skipped 2 records with unrecognized genes.'.format(temp_file_path)),
            mock.call('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
        ]
        mock_logger.info.assert_has_calls(calls)
