import mock
import os
import responses
import tempfile
import shutil
import gzip

from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError

from reference_data.models import GeneInfo, TranscriptInfo, RefseqTranscript

BAD_FIELDS_GTF_DATA = [
    'gene	11869	14412	.	+	.	gene_id "ENSG00000223972.4";\n',
]

GTF_DATA = [
    # Comment
    '#description: evidence-based annotation of the human genome, version 31 (Ensembl 97), mapped to GRCh37 with gencode-backmap\n',
    # Existing gene_id
    'chr1	HAVANA	gene	11869	14409	.	+	.	gene_id "ENSG00000223972.5_2"; gene_type "transcribed_unprocessed_pseudogene"; gene_name "DDX11L1A"; level 2; hgnc_id "HGNC:37102"; havana_gene "OTTHUMG00000000961.2_2"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "overlap";\n',
    # feature_type is 'transcript'
    'chr1	HAVANA	transcript	11869	14409	.	+	.	gene_id "ENSG00000223972.5_2"; transcript_id "ENST00000624735.2_1"; gene_type "transcribed_unprocessed_pseudogene"; gene_name "DDX11L1"; transcript_type "lncRNA"; transcript_name "DDX11L1-202"; level 2; transcript_support_level 1; hgnc_id "HGNC:37102"; tag "basic"; havana_gene "OTTHUMG00000000961.2_2"; havana_transcript "OTTHUMT00000362751.1_1"; remap_num_mappings 1; remap_status "full_contig"; remap_target_status "overlap";\n',
    # feature_type not 'gene', 'transcript', and 'CDS'
    'chr1	HAVANA	exon	11869	12227	.	+	.	gene_id "ENSG00000223972.5_2"; transcript_id "ENST00000456328.2_1"; gene_type "transcribed_unprocessed_pseudogene"; gene_name "DDX11L1"; transcript_type "lncRNA"; transcript_name "DDX11L1-202"; exon_number 1; exon_id "ENSE00002234944.1_1"; level 2; transcript_support_level 1; hgnc_id "HGNC:37102"; tag "basic"; havana_gene "OTTHUMG00000000961.2_2"; havana_transcript "OTTHUMT00000362751.1_1"; remap_original_location "chr1:+:11869-12227"; remap_status "full_contig";\n',
    # Not existing gene_id
    'chr1	HAVANA	gene	621059	622053	.	-	.	gene_id "ENSG00000284662.1_2"; gene_type "protein_coding"; gene_name "OR4F16"; level 2; hgnc_id "HGNC:15079"; havana_gene "OTTHUMG00000002581.3_2"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "overlap";\n',
    'chr1	HAVANA	transcript	621059	622053	.	-	.	gene_id "ENSG00000284662.1_2"; transcript_id "ENST00000332831.4_2"; '
    'gene_type "protein_coding"; gene_name "OR4F16"; transcript_type "protein_coding"; transcript_name "OR4F16-201"; level 2; '
    'protein_id "ENSP00000329982.2"; transcript_support_level "NA"; hgnc_id "HGNC:15079"; tag "basic"; tag "MANE_Select"; tag "CCDS"; '
    'ccdsid "CCDS41221.1"; havana_gene "OTTHUMG00000002581.3_2"; havana_transcript "OTTHUMT00000007334.3_2"; remap_num_mappings 1; '
    'remap_status "full_contig"; remap_target_status "overlap";\n',
    # feature_type is 'CDS'
    # gene_id not in existing_gene_ids and transcript_size > ...
    'chr1	HAVANA	CDS	621099	622034	.	-	0	gene_id "ENSG00000284662.1_2"; transcript_id "ENST00000332831.4_2"; gene_type "protein_coding"; gene_name "OR4F16"; transcript_type "protein_coding"; transcript_name "OR4F16-201"; exon_number 1; exon_id "ENSE00002324228.3"; level 2; protein_id "ENSP00000329982.2"; transcript_support_level "NA"; hgnc_id "HGNC:15079"; tag "basic"; tag "appris_principal_1"; tag "CCDS"; ccdsid "CCDS41221.1"; havana_gene "OTTHUMG00000002581.3_2"; havana_transcript "OTTHUMT00000007334.3_2"; remap_original_location "chr1:-:685719-686654"; remap_status "full_contig";\n',
    # len(record["chrom"]) > 2
    'GL000193.1	HAVANA	gene	77815	78162	.	+	.	gene_id "ENSG00000279783.1_5"; gene_type "processed_pseudogene"; gene_name "AC018692.2"; level 2; havana_gene "OTTHUMG00000189459.1_5"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "new";\n',
]

REFSEQ_DATA = [
    'ENST00000258436.1	NR_026874.2	\n',
    'ENST00000624735.7	NM_015658.4	NP_056473.3\n',
]


class UpdateGencodeTest(TestCase):
    databases = '__all__'
    fixtures = ['users', 'reference_data']

    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.temp_file_path = os.path.join(self.test_dir, 'gencode.v31lift37.annotation.gtf.gz')
        with gzip.open(self.temp_file_path, 'wt') as f:
            f.write(''.join(GTF_DATA))
        with open(self.temp_file_path, 'rb') as f:
            self.gzipped_gtf_data = f.read()

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        shutil.rmtree(self.test_dir)

    @mock.patch('os.path.isfile')
    def test_update_gencode_command_arguments(self, mock_isfile):
        # Test missing test required argument
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode')
        self.assertIn(str(ce.exception), ['Error: argument --gencode-release is required',
                                          'Error: the following arguments are required: --gencode-release'])

        # Test required argument out-of-range
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=18')
        self.assertEqual(str(ce.exception), f'Error: argument --gencode-release: invalid choice: 18 (choose from {", ".join([str(i) for i in range(19, 40)])})')

        # Test genome_version out-of-range
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=19', 'mock_path/tmp', '39')
        self.assertIn(str(ce.exception), ["Error: argument genome_version: invalid choice: '39' (choose from '37', '38')",
                                        "Error: argument genome_version: invalid choice: u'39' (choose from '37', '38')"])

        # Test missing genome_version when a GTF file is provided
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=19', 'mock_path/tmp')
        self.assertEqual(str(ce.exception), "The genome version must also be specified after the gencode GTF file path")

        # Test gencode_release and genome_version mis-matched case 1
        mock_isfile.return_value = True
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=19', 'mock_path/tmp.gz', '38')
        mock_isfile.assert_called_with('mock_path/tmp.gz')
        self.assertEqual(str(ce.exception), "Invalid genome_version: 38. gencode v19 only has a GRCh37 version")

        # Test gencode_release and genome_version mis-matched case 2
        mock_isfile.reset_mock()
        mock_isfile.return_value = True
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=20', 'mock_path/tmp1.gz', '37')
        mock_isfile.assert_called_with('mock_path/tmp1.gz')
        self.assertEqual(str(ce.exception), "Invalid genome_version: 37. gencode v20, v21, v22 only have a GRCh38 version")

        # Test genome_version != 38 requires lifted data
        mock_isfile.reset_mock()
        mock_isfile.return_value = True
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=23', 'mock_path/tmp2.gz', '37')
        mock_isfile.assert_called_with('mock_path/tmp2.gz')
        self.assertEqual(str(ce.exception), "Invalid genome_version for file: mock_path/tmp2.gz. gencode v23 and up must have 'lift' in the filename or genome_version arg must be GRCh38")

    @mock.patch('reference_data.management.commands.utils.gencode_utils.logger')
    def test_update_gencode_command_bad_gtf_data(self, mock_logger):
        # Test wrong number data feilds in a line
        temp_bad_file_path = os.path.join(self.test_dir, 'bad.gencode.v23lift37.annotation.gtf.gz')
        with gzip.open(temp_bad_file_path, 'wt') as f:
            f.write(''.join(BAD_FIELDS_GTF_DATA))
        with self.assertRaises(ValueError) as ve:
            call_command('update_gencode', '--gencode-release=23', temp_bad_file_path, '37')
        self.assertIn(str(ve.exception), ['Unexpected number of fields on line #0: [\'gene\', \'11869\', \'14412\', \'.\', \'+\', \'.\', \'gene_id "ENSG00000223972.4";\']',
                                          'Unexpected number of fields on line #0: [u\'gene\', u\'11869\', u\'14412\', u\'.\', u\'+\', u\'.\', u\'gene_id "ENSG00000223972.4";\']'])
        mock_logger.info.assert_called_with('Loading {} (genome version: 37)'.format(temp_bad_file_path))

    @responses.activate
    @mock.patch('reference_data.management.commands.update_gencode.logger')
    def test_update_gencode_command_url_generation(self, mock_logger):
        # Test the code paths of generating urls, gencode_release == 19
        url_19 = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_19/gencode.v19.annotation.gtf.gz'
        responses.add(responses.HEAD, url_19, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url_19, body=self.gzipped_gtf_data, stream=True)
        call_command('update_gencode', '--gencode-release=19')
        self.assertEqual(responses.calls[0].request.url, url_19)
        responses.reset()

        # Test the code paths of generating urls, gencode_release <= 22
        mock_logger.reset_mock()
        url_20 = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_20/gencode.v20.annotation.gtf.gz'
        responses.add(responses.HEAD, url_20, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url_20, body=self.gzipped_gtf_data, stream=True)
        call_command('update_gencode', '--gencode-release=20')
        self.assertEqual(responses.calls[0].request.url, url_20)
        responses.reset()

        # Test the code paths of generating urls, gencode_release > 22
        mock_logger.reset_mock()
        url_23 = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_23/gencode.v23.annotation.gtf.gz'
        responses.add(responses.HEAD, url_23, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url_23, body=self.gzipped_gtf_data, stream=True)
        url_23_lift = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_23/GRCh37_mapping/gencode.v23lift37.annotation.gtf.gz'
        responses.add(responses.HEAD, url_23_lift, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url_23_lift, body=self.gzipped_gtf_data, stream=True)
        call_command('update_gencode', '--gencode-release=23')
        self.assertEqual(responses.calls[0].request.url, url_23_lift)
        self.assertEqual(responses.calls[2].request.url, url_23)

    def _has_expected_new_genes(self, expected_release=None):
        gene_info = GeneInfo.objects.get(gene_id='ENSG00000223972')
        self.assertEqual(gene_info.gencode_release, expected_release or 27)
        gene_info = GeneInfo.objects.get(gene_id='ENSG00000284662')
        self.assertEqual(gene_info.start_grch37, 621059)
        self.assertEqual(gene_info.chrom_grch37, '1')
        self.assertEqual(gene_info.coding_region_size_grch37, 936)
        self.assertEqual(gene_info.gencode_release, expected_release or 31)
        self.assertEqual(gene_info.gencode_gene_type, 'protein_coding')
        self.assertEqual(gene_info.gene_symbol, 'OR4F16')

    def _has_expected_new_transcripts(self, expected_release=27, updated_existing_trancript=True):
        trans_info = TranscriptInfo.objects.get(transcript_id='ENST00000624735')
        self.assertEqual(trans_info.gene.gene_id, 'ENSG00000223972' if updated_existing_trancript else 'ENSG00000227232')
        self.assertEqual(trans_info.gene.gencode_release, expected_release)
        self.assertFalse(trans_info.is_mane_select)
        trans_info = TranscriptInfo.objects.get(transcript_id='ENST00000332831')
        self.assertEqual(trans_info.start_grch37, 621059)
        self.assertEqual(trans_info.end_grch37, 622053)
        self.assertEqual(trans_info.strand_grch37, '-')
        self.assertEqual(trans_info.chrom_grch37, '1')
        self.assertEqual(trans_info.gene.gene_id, 'ENSG00000284662')
        self.assertEqual(trans_info.gene.gencode_release, 39 if expected_release == 39 else 31)
        self.assertTrue(trans_info.is_mane_select)

    def _add_latest_responses(self):
        url = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/gencode.v39.annotation.gtf.gz'
        responses.add(responses.HEAD, url, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url, body=self.gzipped_gtf_data, stream=True)
        url_lift = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/GRCh37_mapping/gencode.v39lift37.annotation.gtf.gz'
        responses.add(responses.HEAD, url_lift, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url_lift, body=self.gzipped_gtf_data, stream=True)
        return url, url_lift

    @responses.activate
    @mock.patch('reference_data.management.commands.utils.gencode_utils.logger')
    @mock.patch('reference_data.management.commands.update_gencode_transcripts.logger')
    @mock.patch('reference_data.management.commands.update_gencode.logger')
    def test_update_gencode_command(self, mock_logger, mock_update_transcripts_logger, mock_utils_logger):
        # Test normal command function
        call_command('update_gencode', '--gencode-release=31', self.temp_file_path, '37')
        mock_utils_logger.info.assert_has_calls([
            mock.call('Loading {} (genome version: 37)'.format(self.temp_file_path)),
            mock.call('Creating 1 TranscriptInfo records'),
        ])
        calls = [
            mock.call('Creating 1 GeneInfo records'),
            mock.call('Done'),
            mock.call('Stats: '),
            mock.call('  genes_skipped: 1'),
            mock.call('  transcripts_skipped: 1'),
            mock.call('  genes_created: 1'),
            mock.call('  transcripts_created: 1')
        ]
        mock_logger.info.assert_has_calls(calls)

        self._has_expected_new_genes()

        self.assertEqual(TranscriptInfo.objects.all().count(), 3)
        self._has_expected_new_transcripts(updated_existing_trancript=False)

        # Test normal command function with a --reset option
        mock_logger.reset_mock()
        call_command('update_gencode', '--reset', '--gencode-release=39', self.temp_file_path, '37')
        mock_utils_logger.info.assert_has_calls([
            mock.call('Loading {} (genome version: 37)'.format(self.temp_file_path)),
            mock.call('Creating 2 TranscriptInfo records'),
        ])
        calls = [
            mock.call('Dropping the 3 existing TranscriptInfo entries'),
            mock.call('Dropping the 50 existing GeneInfo entries'),
            mock.call('Creating 2 GeneInfo records'),
            mock.call('Done'),
            mock.call('Stats: '),
            mock.call('  genes_created: 2'),
            mock.call('  transcripts_created: 2')
        ]
        mock_logger.info.assert_has_calls(calls)

        self.assertEqual(GeneInfo.objects.all().count(), 2)
        gene_info = GeneInfo.objects.get(gene_id = 'ENSG00000223972')
        self.assertEqual(gene_info.gencode_release, 39)
        gene_info = GeneInfo.objects.get(gene_id = 'ENSG00000284662')
        self.assertEqual(gene_info.start_grch37, 621059)
        self.assertEqual(gene_info.chrom_grch37, '1')
        self.assertEqual(gene_info.coding_region_size_grch37, 936)
        self.assertEqual(gene_info.gencode_release, 39)
        self.assertEqual(gene_info.gencode_gene_type, 'protein_coding')
        self.assertEqual(gene_info.gene_id, 'ENSG00000284662')
        self.assertEqual(gene_info.gene_symbol, 'OR4F16')
        self.assertEqual(gene_info.end_grch37, 622053)
        self.assertEqual(gene_info.strand_grch37, '-')

        # Test only reloading transcripts
        url, url_lift = self._add_latest_responses()
        call_command('update_gencode_transcripts')

        self.assertEqual(GeneInfo.objects.all().count(), 2)
        self.assertEqual(TranscriptInfo.objects.all().count(), 2)
        self._has_expected_new_transcripts(expected_release=39)
        mock_utils_logger.info.assert_has_calls([
            mock.call('Loading {} (genome version: 37)'.format(self.temp_file_path)),
            mock.call('Creating 2 TranscriptInfo records'),
        ])
        mock_update_transcripts_logger.info.assert_has_calls([
            mock.call('Dropping the 2 existing TranscriptInfo entries'),
        ])

        self.assertEqual(responses.calls[0].request.url, url_lift)
        self.assertEqual(responses.calls[2].request.url, url)

    @responses.activate
    @mock.patch('reference_data.management.commands.utils.update_utils.logger')
    @mock.patch('reference_data.management.commands.utils.gencode_utils.logger')
    @mock.patch('reference_data.management.commands.update_gencode_latest.logger')
    def test_update_gencode_latest_command(self, mock_logger, mock_gencode_utils_logger, mock_update_utils_logger):
        self._add_latest_responses()
        refseq_url = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/gencode.v39.metadata.RefSeq.gz'
        responses.add(responses.HEAD, refseq_url, headers={"Content-Length": "1024"})
        responses.add(responses.GET, refseq_url, body=gzip.compress(''.join(REFSEQ_DATA).encode()))

        call_command('update_gencode_latest', '--track-symbol-change', f'--output-dir={self.test_dir}')
        mock_gencode_utils_logger.info.assert_called_with('Creating 2 TranscriptInfo records')
        mock_logger.info.assert_has_calls([
            mock.call('Updating 1 previously loaded GeneInfo records'),
            mock.call('Creating 1 GeneInfo records'),
            mock.call('Dropping 1 existing TranscriptInfo entries'),
            mock.call('Done'),
            mock.call('Stats: '),
            mock.call('  genes_updated: 1'),
            mock.call('  genes_created: 1'),
            mock.call('  transcripts_replaced: 1'),
            mock.call('  transcripts_created: 1'),
        ])
        mock_update_utils_logger.info.assert_has_calls([
            mock.call('Parsing file'),
            mock.call('Deleting 1 existing RefseqTranscript records'),
            mock.call('Creating 2 RefseqTranscript records'),
            mock.call('Done'),
        ])

        self._has_expected_new_genes(expected_release=39)

        self.assertEqual(TranscriptInfo.objects.all().count(), 3)
        self._has_expected_new_transcripts(expected_release=39)

        self.assertEqual(RefseqTranscript.objects.count(), 2)
        self.assertListEqual(
            list(RefseqTranscript.objects.order_by('transcript_id').values('transcript__transcript_id', 'refseq_id')), [
                {'transcript__transcript_id': 'ENST00000258436', 'refseq_id': 'NR_026874.2'},
                {'transcript__transcript_id': 'ENST00000624735', 'refseq_id': 'NM_015658.4'}
            ])

        with open(f'{self.test_dir}/gene_symbol_changes.csv') as f:
            self.assertListEqual(f.readlines(), ['ENSG00000223972,DDX11L1,DDX11L1A\n'])
