import mock

import json
import re

from django.core.management.base import CommandError

from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase
from reference_data.models import Omim, GeneInfo

OMIM_DATA = [
    '# Copyright (c) 1966-2020 Johns Hopkins University. Use of this file adheres to the terms specified at https://omim.org/help/agreement.\n',
    '# Chromosome	Genomic Position Start	Genomic Position End	Cyto Location	Computed Cyto Location	MIM Number	Gene/Locus And Other Related Symbols	Gene Name	Approved Gene Symbol	Entrez Gene ID	Ensembl Gene ID	Comments	Phenotypes	Mouse Gene Symbol/ID\n',
    'chr1	1	27600000	1p36		607413	OR4F29	Alzheimer disease neuronal thread protein						\n',
    'chr1	1	27600000	1p36		612367	OR4F5	Alkaline phosphatase, plasma level of, QTL 2		100196914		linkage with rs1780324	{Alkaline phosphatase, plasma level of, QTL 2}, 612367 (2)	\n',
    '# comment line\n',
    'chr1	1	123400000	1p		606788		Anorexia nervosa, susceptibility to, 1		171514			{Anorexia nervosa, susceptibility to, 1}, 606788 (2)	\n',
    'chr1	1	567800000	1p36		605462	BCC1	Basal cell carcinoma, susceptibility to, 1		100307118		associated with rs7538876	{Basal cell carcinoma, susceptibility to, 1}, 605462 (2)	\n',
    'chr6			6p13		621133	OGFRl1	Opioid growth factor receptor-like protein 1						\n',
]

CACHED_OMIM_DATA = "ensembl_gene_id\tmim_number\tgene_description\tcomments\tphenotype_description\tphenotype_mim_number\tphenotype_map_method\tphenotype_inheritance\tchrom\tstart\tend\nENSG00000235249\t607413\tAlzheimer disease neuronal thread protein\t\t\t\t\t\t1\t1\t27600000\nENSG00000186092\t612367\tAlkaline phosphatase, plasma level of, QTL 2\tlinkage with rs1780324\tAlkaline phosphatase, plasma level of, QTL 2\t612367\t2\t\t1\t1\t27600000\n\t606788\tAnorexia nervosa, susceptibility to, 1\t\tAnorexia nervosa, susceptibility to, 1\t606788\t2\t\t1\t1\t123400000\n\t605462\tBasal cell carcinoma, susceptibility to, 1\tassociated with rs7538876\tBasal cell carcinoma, susceptibility to, 1\t605462\t2\t\t1\t1\t567800000"

LAST_MODIFIED = 'Fri, 21 Mar 2025 10:02:00 GMT'
HEAD_RESPONSE = {'headers': {'Content-Length': '1024', 'Last-Modified': LAST_MODIFIED}}

class UpdateOmimTest(ReferenceDataCommandTestCase):

    URL = 'https://data.omim.org/downloads/test_key/genemap2.txt'
    DATA = OMIM_DATA

    def setUp(self):
        super().setUp()
        self.mock_get_file_last_modified_patcher.stop()
        patcher = mock.patch('reference_data.models.GenCC.get_current_version')
        patcher.start().return_value = self.mock_get_file_last_modified.return_value
        self.addCleanup(patcher.stop)

    def test_update_omim_command_exceptions(self):
        # Test omim account expired
        self._run_error_command(['This account has expired'],'This account has expired')

        # Test bad omim data header
        self._run_error_command([OMIM_DATA[2]], 'Header row not found in genemap2 file before line 0: chr1	1	27600000	1p36		607413	OR4F29	Alzheimer disease neuronal thread protein						')

        # Test bad phenotype field in the record
        bad_phenotype_data = OMIM_DATA[:2]
        bad_phenotype_data.append('chr1	0	27600000	1p36		605462	BCC1	Basal cell carcinoma, susceptibility to, 1		100307118		associated with rs7538876	{x}, 605462 (5)	\n')
        self._run_error_command(bad_phenotype_data, None)
        error_message = self.mock_command_logger.error.mock_calls[-1].args[0]
        record = json.loads(re.search(r'unable to update Omim: No phenotypes found: ({.*})', error_message).group(1))
        self.assertDictEqual(record, {"gene_name": "Basal cell carcinoma, susceptibility to, 1", "mim_number": "605462", "comments": "associated with rs7538876", "mouse_gene_symbol/id": "", "phenotypes": "{x}, 605462 (5)", "genomic_position_end": "27600000", "ensembl_gene_id": "", "gene/locus_and_other_related_symbols": "BCC1", "approved_gene_symbol": "", "entrez_gene_id": "100307118", "computed_cyto_location": "", "cyto_location": "1p36", "#_chromosome": "chr1", "genomic_position_start": "0"})

        self.assertEqual(Omim.objects.all().count(), 3)

        GeneInfo.objects.all().delete()
        self._run_error_command(self.DATA, 'Related data is missing to load Omim: gene_ids_to_gene, gene_symbols_to_gene')

    def _run_error_command(self, data, error):
        with self.assertRaises(CommandError) as e:
            self._run_command(data, command_args=['--omim-key=test_key'], head_response=HEAD_RESPONSE)
        self.assertEqual(str(e.exception), 'Failed to Update: Omim')
        if error:
            self.mock_command_logger.error.assert_called_with(f'unable to update Omim: {error}')


    @mock.patch('seqr.utils.file_utils.logger')
    @mock.patch('seqr.views.utils.export_utils.open')
    @mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_update_omim_command(self, mock_subprocess, mock_temp_dir, mock_open,mock_file_utils_logger):
        mock_subprocess.return_value.wait.return_value = 0
        mock_temp_dir.return_value.__enter__.return_value = '/mock/tmp'

        self._test_update_omim_command(command_args=['--omim-key=test_key'])

        calls = [
            mock.call('==> gsutil mv /mock/tmp/* gs://seqr-reference-data/omim/', None),
        ]
        mock_file_utils_logger.info.assert_has_calls(calls)

        mock_subprocess.assert_called_with('gsutil mv /mock/tmp/* gs://seqr-reference-data/omim/', stdout=-1, stderr=-2, shell=True)  # nosec
        mock_open.assert_called_with('/mock/tmp/parsed_omim_records__latest.txt', 'w')
        self.assertEqual(mock_open.return_value.__enter__.return_value.write.call_args.args[0], CACHED_OMIM_DATA)

    def _test_update_omim_command(self, **kwargs):
        self._test_update_command(
            'Omim', LAST_MODIFIED, existing_records=3, created_records=4, skipped_records=0,
            head_response=HEAD_RESPONSE, **kwargs,
        )
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

    def test_update_omim_cached_records(self):
        self.URL = 'https://storage.googleapis.com/seqr-reference-data/omim/parsed_omim_records__latest.txt'
        self.DATA = [CACHED_OMIM_DATA]
        self._test_update_omim_command()
