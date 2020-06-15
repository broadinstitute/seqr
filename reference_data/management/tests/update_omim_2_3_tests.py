import mock

import os
import tempfile
import shutil
import responses
import json
import re

from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError

from reference_data.models import Omim

OMIM_DATA = [
    '# Copyright (c) 1966-2020 Johns Hopkins University. Use of this file adheres to the terms specified at https://omim.org/help/agreement.\n',
    '# Chromosome	Genomic Position Start	Genomic Position End	Cyto Location	Computed Cyto Location	MIM Number	Gene Symbols	Gene Name	Approved Symbol	Entrez Gene ID	Ensembl Gene ID	Comments	Phenotypes	Mouse Gene Symbol/ID\n',
    'chr1	0	27600000	1p36		607413	OR4F29	Alzheimer disease neuronal thread protein						\n',
    'chr1	0	27600000	1p36		612367	OR4F5	Alkaline phosphatase, plasma level of, QTL 2		100196914		linkage with rs1780324	{Alkaline phosphatase, plasma level of, QTL 2}, 612367 (2)	\n',
    '# comment line\n',
    'chr1	0	123400000	1p		606788	ANON1	Anorexia nervosa, susceptibility to, 1		171514			{Anorexia nervosa, susceptibility to, 1}, 606788 (2)	\n',
    'chr1	0	27600000	1p36		605462	BCC1	Basal cell carcinoma, susceptibility to, 1		100307118		associated with rs7538876	{Basal cell carcinoma, susceptibility to, 1}, 605462 (2)	\n',
]

OMIM_ENTRIES = {
    "omim": {
        "version": "1.0",
        "entryList": [
            {
                "entry": {
                    "prefix": "#",
                    "mimNumber": 612367,
                    "status": "live",
                    "titles": {
                        "preferredTitle": "IMMUNODEFICIENCY 38 WITH BASAL GANGLIA CALCIFICATION; IMD38",
                        "alternativeTitles": "IMMUNODEFICIENCY 38, MYCOBACTERIOSIS, AUTOSOMAL RECESSIVE;;\nISG15 DEFICIENCY, AUTOSOMAL RECESSIVE"
                    },
                    "geneMap": {
                    "phenotypeMapList": [
                        {
                            "phenotypeMap": {
                                "mimNumber": 147571,
                                "phenotype": "Immunodeficiency 38",
                                "phenotypeMimNumber": 612367,
                                "phenotypeMappingKey": 3,
                                "phenotypeInheritance": "Autosomal recessive",
                                "phenotypicSeriesNumber": "PS300755",
                                "sequenceID": 7271,
                                "chromosome": 1,
                                "chromosomeSymbol": "1",
                                "chromosomeSort": 23,
                                "chromosomeLocationStart": 1013496,
                                "chromosomeLocationEnd": 1014539,
                                "transcript": "ENST00000649529.1",
                                "cytoLocation": "1p36.33",
                                "computedCytoLocation": "1p36.33",
                                "geneSymbols": "ISG15, G1P2, IFI15, IMD38"
                            }
                        }
                    ]}
                }
            },
        ]
    }
}


class UpdateOmimTest(TestCase):
    fixtures = ['users', 'reference_data']
    multi_db = True

    def setUp(self):
        # Create a temporary directory and a test data file
        self.test_dir = tempfile.mkdtemp()
        self.temp_file_path = os.path.join(self.test_dir, 'genemap2.txt')
        with open(self.temp_file_path, 'w') as f:
            f.write(''.join(OMIM_DATA))

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        shutil.rmtree(self.test_dir)

    @responses.activate
    @mock.patch('reference_data.management.commands.update_omim.os')
    @mock.patch('reference_data.management.commands.utils.update_utils.download_file')
    def test_update_omim_command_exceptions(self, mock_download, mock_os):
        # Test required argument
        mock_os.environ.get.return_value = ''
        with self.assertRaises(CommandError) as ce:
            call_command('update_omim')
        self.assertEqual(str(ce.exception), 'omim_key is required')

        # Test omim account expired
        temp_bad_file_path = os.path.join(self.test_dir, 'bad_response.txt')
        with open(temp_bad_file_path, 'w') as f:
            f.write('This account has expired')
        mock_download.return_value = temp_bad_file_path
        with self.assertRaises(Exception) as err:
            call_command('update_omim', '--omim-key=test_key')
        self.assertEqual(str(err.exception), 'This account has expired')

        # Test bad omim data header
        with open(temp_bad_file_path, 'w') as f:
            f.write(OMIM_DATA[2])
        mock_download.return_value = temp_bad_file_path
        with self.assertRaises(ValueError) as ve:
            call_command('update_omim', '--omim-key=test_key')
        self.assertEqual(str(ve.exception), 'Header row not found in genemap2 file before line 0: chr1	0	27600000	1p36		607413	OR4F29	Alzheimer disease neuronal thread protein						')

        # Test empty phenotype description, not reachable
        # Test invalid phenotype map method choice, not reachable

        # Test bad phenotype field in the record
        with open(temp_bad_file_path, 'w') as f:
            f.write(''.join(OMIM_DATA[:2]))
            f.write('chr1	0	27600000	1p36		605462	BCC1	Basal cell carcinoma, susceptibility to, 1		100307118		associated with rs7538876	bad_phenotype_field	\n')
        mock_download.return_value = temp_bad_file_path
        with self.assertRaises(ValueError) as ve:
            call_command('update_omim', '--omim-key=test_key')
        record = json.loads(re.search(r'No phenotypes found: ({.*})', str(ve.exception)).group(1))
        self.assertDictEqual(record, {"gene_name": "Basal cell carcinoma, susceptibility to, 1", "mim_number": "605462", "comments": "associated with rs7538876", "mouse_gene_symbol/id": "", "phenotypes": "bad_phenotype_field", "genomic_position_end": "27600000", "ensembl_gene_id": "", "gene_symbols": "BCC1", "approved_symbol": "", "entrez_gene_id": "100307118", "computed_cyto_location": "", "cyto_location": "1p36", "#_chromosome": "chr1", "genomic_position_start": "0"})

    @responses.activate
    @mock.patch('reference_data.management.commands.utils.update_utils.logger')
    @mock.patch('reference_data.management.commands.update_omim.logger')
    @mock.patch('reference_data.management.commands.utils.update_utils.download_file')
    def test_update_omim_command(self, mock_download, mock_omim_logger, mock_utils_logger):
        mock_download.return_value = self.temp_file_path

        # Test omim api response error
        responses.add(responses.GET, 'https://api.omim.org/api/entry?apiKey=test_key&include=geneMap&format=json&mimNumber=612367',
                      json={'error': 'not found'}, status=400)
        # Test omim api responses with bad data
        responses.add(responses.GET, 'https://api.omim.org/api/entry?apiKey=test_key&include=geneMap&format=json&mimNumber=612367',
                      json={"omim": {"entryList": []}}, status=200)
        # Normal omim api responses
        responses.add(responses.GET, 'https://api.omim.org/api/entry?apiKey=test_key&include=geneMap&format=json&mimNumber=612367',
                      json=OMIM_ENTRIES, status=200)

        # Omim api response error test
        with self.assertRaises(CommandError) as ce:
            call_command('update_omim', '--omim-key=test_key')
        self.assertEqual(str(ce.exception), 'Request failed with 400: Bad Request')

        # Bad omim api response test
        with self.assertRaises(CommandError) as ce:
            call_command('update_omim', '--omim-key=test_key')
        self.assertEqual(str(ce.exception), 'Expected 1 omim entries but recieved 0')

        # Test without a file_path parameter
        mock_utils_logger.reset_mock()
        call_command('update_omim', '--omim-key=test_key')

        mock_download.assert_called_with('https://data.omim.org/downloads/test_key/genemap2.txt')

        calls = [
            mock.call('Deleting 0 existing Omim records'),
            mock.call('Parsing file'),
            mock.call('Creating 2 Omim records'),
            mock.call('Done'),
            mock.call('Loaded 2 Omim records from {}. Skipped 2 records with unrecognized genes.'.format(self.temp_file_path)),
            mock.call('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
        ]
        mock_utils_logger.info.assert_has_calls(calls)
        calls = [
            mock.call('Adding phenotypic series information'),
            mock.call('Found 1 records with phenotypic series')
        ]
        mock_omim_logger.info.assert_has_calls(calls)
        mock_omim_logger.debug.assert_called_with('Fetching entries 0-20')

        # test with a file_path parameter
        mock_download.reset_mock()
        mock_utils_logger.reset_mock()
        mock_omim_logger.reset_mock()
        call_command('update_omim', '--omim-key=test_key', self.temp_file_path)
        mock_download.assert_not_called()
        calls = [
            mock.call('Deleting 2 existing Omim records'),
            mock.call('Parsing file'),
            mock.call('Creating 2 Omim records'),
            mock.call('Done'),
            mock.call('Loaded 2 Omim records from {}. Skipped 2 records with unrecognized genes.'.format(self.temp_file_path)),
            mock.call('Running ./manage.py update_gencode to update the gencode version might fix missing genes')
        ]
        mock_utils_logger.info.assert_has_calls(calls)
        calls = [
            mock.call('Adding phenotypic series information'),
            mock.call('Found 1 records with phenotypic series')
        ]
        mock_omim_logger.info.assert_has_calls(calls)
        mock_omim_logger.debug.assert_called_with('Fetching entries 0-20')

        self.assertEqual(Omim.objects.all().count(), 2)
        record = Omim.objects.get(gene__gene_symbol = 'OR4F5')
        self.assertEqual(record.comments, 'linkage with rs1780324')
        self.assertEqual(record.gene_description, 'Alkaline phosphatase, plasma level of, QTL 2')
        self.assertEqual(record.mim_number, 612367)
        self.assertEqual(record.phenotype_description, 'Alkaline phosphatase, plasma level of, QTL 2')
        self.assertEqual(record.phenotype_inheritance, None)
        self.assertEqual(record.phenotype_map_method, '2')
        self.assertEqual(record.phenotype_mim_number, 612367)
        self.assertEqual(record.phenotypic_series_number, 'PS300755')
