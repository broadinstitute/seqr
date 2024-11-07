import mock

import tempfile
import responses
import json
import re

from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError

from reference_data.management.commands.update_omim import CachedOmimReferenceDataHandler
from reference_data.models import Omim, GeneInfo

OMIM_DATA = [
    '# Copyright (c) 1966-2020 Johns Hopkins University. Use of this file adheres to the terms specified at https://omim.org/help/agreement.\n',
    '# Chromosome	Genomic Position Start	Genomic Position End	Cyto Location	Computed Cyto Location	MIM Number	Gene/Locus And Other Related Symbols	Gene Name	Approved Gene Symbol	Entrez Gene ID	Ensembl Gene ID	Comments	Phenotypes	Mouse Gene Symbol/ID\n',
    'chr1	1	27600000	1p36		607413	OR4F29	Alzheimer disease neuronal thread protein						\n',
    'chr1	1	27600000	1p36		612367	OR4F5	Alkaline phosphatase, plasma level of, QTL 2		100196914		linkage with rs1780324	{Alkaline phosphatase, plasma level of, QTL 2}, 612367 (2)	\n',
    '# comment line\n',
    'chr1	1	123400000	1p		606788		Anorexia nervosa, susceptibility to, 1		171514			{Anorexia nervosa, susceptibility to, 1}, 606788 (2)	\n',
    'chr1	1	567800000	1p36		605462	BCC1	Basal cell carcinoma, susceptibility to, 1		100307118		associated with rs7538876	{Basal cell carcinoma, susceptibility to, 1}, 605462 (2)	\n',
]

CACHED_OMIM_DATA = "ENSG00000235249\t607413\tAlzheimer disease neuronal thread protein\t\t\t\t\t\t1\t1\t27600000\nENSG00000186092\t612367\tAlkaline phosphatase, plasma level of, QTL 2\tlinkage with rs1780324\tAlkaline phosphatase, plasma level of, QTL 2\t612367\t2\t\t1\t1\t27600000\n\t606788\tAnorexia nervosa, susceptibility to, 1\t\tAnorexia nervosa, susceptibility to, 1\t606788\t2\t\t1\t1\t123400000\n\t605462\tBasal cell carcinoma, susceptibility to, 1\tassociated with rs7538876\tBasal cell carcinoma, susceptibility to, 1\t605462\t2\t\t1\t1\t567800000"


class UpdateOmimTest(TestCase):
    databases = '__all__'
    fixtures = ['users', 'reference_data']

    @responses.activate
    @mock.patch('reference_data.management.commands.utils.update_utils.logger')
    @mock.patch('reference_data.management.commands.update_omim.os')
    def test_update_omim_command_exceptions(self, mock_os, mock_logger):
        url = 'https://data.omim.org/downloads/test_key/genemap2.txt'
        responses.add(responses.HEAD, url, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url, body='This account has expired')
        responses.add(responses.GET, url, body=OMIM_DATA[2])
        bad_phenotype_data = OMIM_DATA[:2]
        bad_phenotype_data.append('chr1	0	27600000	1p36		605462	BCC1	Basal cell carcinoma, susceptibility to, 1		100307118		associated with rs7538876	{x}, 605462 (5)	\n')
        responses.add(responses.GET, url, body=''.join(bad_phenotype_data))
        responses.add(responses.GET, url, body=''.join(OMIM_DATA))

        # Test required argument
        mock_os.environ.get.return_value = ''
        with self.assertRaises(CommandError) as ce:
            call_command('update_omim')
        self.assertEqual(str(ce.exception), 'omim_key is required')

        # Test omim account expired
        call_command('update_omim', '--omim-key=test_key')
        mock_logger.error.assert_called_with('This account has expired', extra={'traceback': mock.ANY})

        # Test bad omim data header
        call_command('update_omim', '--omim-key=test_key')
        mock_logger.error.assert_called_with('Header row not found in genemap2 file before line 0: chr1	1	27600000	1p36		607413	OR4F29	Alzheimer disease neuronal thread protein						', extra={'traceback': mock.ANY})

        # Test bad phenotype field in the record
        call_command('update_omim', '--omim-key=test_key')
        record = json.loads(re.search(r'No phenotypes found: ({.*})', mock_logger.error.call_args.args[0]).group(1))
        self.assertDictEqual(record, {"gene_name": "Basal cell carcinoma, susceptibility to, 1", "mim_number": "605462", "comments": "associated with rs7538876", "mouse_gene_symbol/id": "", "phenotypes": "{x}, 605462 (5)", "genomic_position_end": "27600000", "ensembl_gene_id": "", "gene/locus_and_other_related_symbols": "BCC1", "approved_gene_symbol": "", "entrez_gene_id": "100307118", "computed_cyto_location": "", "cyto_location": "1p36", "#_chromosome": "chr1", "genomic_position_start": "0"})

        self.assertEqual(Omim.objects.all().count(), 3)

        GeneInfo.objects.all().delete()
        with self.assertRaises(CommandError) as ve:
            call_command('update_omim', '--omim-key=test_key')
        self.assertEqual(str(ve.exception), "GeneInfo table is empty. Run './manage.py update_gencode' before running this command.")


    @responses.activate
    @mock.patch('reference_data.management.commands.utils.update_utils.logger')
    @mock.patch('reference_data.management.commands.update_omim.logger')
    @mock.patch('reference_data.management.commands.utils.download_utils.tempfile')
    @mock.patch('reference_data.management.commands.update_omim.os')
    def test_update_omim_command(self, mock_os, mock_tempfile, mock_omim_logger, mock_utils_logger):
        tmp_dir = tempfile.gettempdir()
        mock_tempfile.gettempdir.return_value = tmp_dir
        tmp_file = '{}/genemap2.txt'.format(tmp_dir)

        data_url = 'https://data.omim.org/downloads/test_key/genemap2.txt'
        responses.add(responses.HEAD, data_url, headers={"Content-Length": "1024"})
        responses.add(responses.GET, data_url, body=''.join(OMIM_DATA))

        # Test without a file_path parameter
        mock_utils_logger.reset_mock()
        call_command('update_omim', '--omim-key=test_key', '--skip-cache-parsed-records')

        calls = [
            mock.call('Parsing file'),
            mock.call('Deleting 3 existing Omim records'),
            mock.call('Creating 4 Omim records'),
            mock.call('Done'),
            mock.call('Loaded 4 Omim records from {}. Skipped 0 records with unrecognized genes.'.format(tmp_file)),
        ]
        mock_utils_logger.info.assert_has_calls(calls)
        mock_os.system.assert_not_called()

        # test with a file_path parameter
        responses.remove(responses.GET, data_url)
        mock_utils_logger.reset_mock()
        mock_omim_logger.reset_mock()
        call_command('update_omim', '--omim-key=test_key', tmp_file)
        calls = [
            mock.call('Parsing file'),
            mock.call('Deleting 4 existing Omim records'),
            mock.call('Creating 4 Omim records'),
            mock.call('Done'),
            mock.call('Loaded 4 Omim records from {}. Skipped 0 records with unrecognized genes.'.format(tmp_file)),
        ]
        mock_utils_logger.info.assert_has_calls(calls)
        calls = [
            mock.call('gsutil mv parsed_omim_records.txt gs://seqr-reference-data/omim/'),
        ]
        mock_omim_logger.info.assert_has_calls(calls)

        mock_os.system.assert_called_with('gsutil mv parsed_omim_records.txt gs://seqr-reference-data/omim/')
        with open('parsed_omim_records.txt', 'r') as f:
            self.assertEqual(f.read(), CACHED_OMIM_DATA)

        self._assert_has_expected_omim_records()

    def _assert_has_expected_omim_records(self):
        self.assertEqual(Omim.objects.all().count(), 4)
        record = Omim.objects.get(gene__gene_symbol='OR4F5')
        self.assertEqual(record.comments, 'linkage with rs1780324')
        self.assertEqual(record.gene_description, 'Alkaline phosphatase, plasma level of, QTL 2')
        self.assertEqual(record.mim_number, 612367)
        self.assertEqual(record.phenotype_description, 'Alkaline phosphatase, plasma level of, QTL 2')
        self.assertEqual(record.phenotype_inheritance, None)
        self.assertEqual(record.phenotype_map_method, '2')
        self.assertEqual(record.phenotype_mim_number, 612367)
        self.assertEqual(record.chrom, '1')
        self.assertEqual(record.start, 1)
        self.assertEqual(record.end, 27600000)

        no_gene_record = Omim.objects.get(phenotype_mim_number=605462)
        self.assertIsNone(no_gene_record.gene)
        self.assertEqual(no_gene_record.comments, 'associated with rs7538876')
        self.assertEqual(no_gene_record.gene_description, 'Basal cell carcinoma, susceptibility to, 1')
        self.assertEqual(no_gene_record.mim_number, 605462)
        self.assertEqual(no_gene_record.phenotype_description, 'Basal cell carcinoma, susceptibility to, 1')
        self.assertEqual(no_gene_record.phenotype_inheritance, None)
        self.assertEqual(no_gene_record.phenotype_map_method, '2')
        self.assertEqual(no_gene_record.chrom, '1')
        self.assertEqual(no_gene_record.start, 1)
        self.assertEqual(no_gene_record.end, 567800000)

    @responses.activate
    @mock.patch('reference_data.management.commands.utils.update_utils.logger')
    @mock.patch('reference_data.management.commands.utils.download_utils.tempfile')
    def test_update_omim_cached_records(self, mock_tempfile, mock_utils_logger):
        tmp_dir = tempfile.gettempdir()
        mock_tempfile.gettempdir.return_value = tmp_dir
        tmp_file = '{}/parsed_omim_records.txt'.format(tmp_dir)

        data_url = 'https://storage.googleapis.com/seqr-reference-data/omim/parsed_omim_records.txt'
        responses.add(responses.HEAD, data_url, headers={"Content-Length": "1024"})
        responses.add(responses.GET, data_url, body=CACHED_OMIM_DATA)

        CachedOmimReferenceDataHandler().update_records()

        calls = [
            mock.call('Parsing file'),
            mock.call('Deleting 3 existing Omim records'),
            mock.call('Creating 4 Omim records'),
            mock.call('Done'),
            mock.call('Loaded 4 Omim records from {}. Skipped 0 records with unrecognized genes.'.format(tmp_file)),
        ]
        mock_utils_logger.info.assert_has_calls(calls)

        self._assert_has_expected_omim_records()

