import mock
import os
import tempfile
import shutil
import gzip

from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError

from reference_data.models import GeneInfo, TranscriptInfo

BAD_FIELDS_GTF_DATA = [
    'gene	11869	14412	.	+	.	gene_id "ENSG00000223972.4";\n',
]

GTF_DATA = [
    # Comment
    '#description: evidence-based annotation of the human genome, version 31 (Ensembl 97), mapped to GRCh37 with gencode-backmap\n',
    # Existing gene_id
    'chr1	HAVANA	gene	11869	14409	.	+	.	gene_id "ENSG00000223972.5_2"; gene_type "transcribed_unprocessed_pseudogene"; gene_name "DDX11L1"; level 2; hgnc_id "HGNC:37102"; havana_gene "OTTHUMG00000000961.2_2"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "overlap";\n',
    # feature_type is 'transcript'
    'chr1	HAVANA	transcript	11869	14409	.	+	.	gene_id "ENSG00000223972.5_2"; transcript_id "ENST00000456328.2_1"; gene_type "transcribed_unprocessed_pseudogene"; gene_name "DDX11L1"; transcript_type "lncRNA"; transcript_name "DDX11L1-202"; level 2; transcript_support_level 1; hgnc_id "HGNC:37102"; tag "basic"; havana_gene "OTTHUMG00000000961.2_2"; havana_transcript "OTTHUMT00000362751.1_1"; remap_num_mappings 1; remap_status "full_contig"; remap_target_status "overlap";\n',
    # feature_type not 'gene', 'transcript', and 'CDS'
    'chr1	HAVANA	exon	11869	12227	.	+	.	gene_id "ENSG00000223972.5_2"; transcript_id "ENST00000456328.2_1"; gene_type "transcribed_unprocessed_pseudogene"; gene_name "DDX11L1"; transcript_type "lncRNA"; transcript_name "DDX11L1-202"; exon_number 1; exon_id "ENSE00002234944.1_1"; level 2; transcript_support_level 1; hgnc_id "HGNC:37102"; tag "basic"; havana_gene "OTTHUMG00000000961.2_2"; havana_transcript "OTTHUMT00000362751.1_1"; remap_original_location "chr1:+:11869-12227"; remap_status "full_contig";\n',
    # Not existing gene_id
    'chr1	HAVANA	gene	621059	622053	.	-	.	gene_id "ENSG00000284662.1_2"; gene_type "protein_coding"; gene_name "OR4F16"; level 2; hgnc_id "HGNC:15079"; havana_gene "OTTHUMG00000002581.3_2"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "overlap";\n',
    'chr1	HAVANA	transcript	621059	622053	.	-	.	gene_id "ENSG00000284662.1_2"; transcript_id "ENST00000332831.4_2"; gene_type "protein_coding"; gene_name "OR4F16"; transcript_type "protein_coding"; transcript_name "OR4F16-201"; level 2; protein_id "ENSP00000329982.2"; transcript_support_level "NA"; hgnc_id "HGNC:15079"; tag "basic"; tag "appris_principal_1"; tag "CCDS"; ccdsid "CCDS41221.1"; havana_gene "OTTHUMG00000002581.3_2"; havana_transcript "OTTHUMT00000007334.3_2"; remap_num_mappings 1; remap_status "full_contig"; remap_target_status "overlap";\n',
    # feature_type is 'CDS'
    # gene_id not in existing_gene_ids and transcript_size > ...
    'chr1	HAVANA	CDS	621099	622034	.	-	0	gene_id "ENSG00000284662.1_2"; transcript_id "ENST00000332831.4_2"; gene_type "protein_coding"; gene_name "OR4F16"; transcript_type "protein_coding"; transcript_name "OR4F16-201"; exon_number 1; exon_id "ENSE00002324228.3"; level 2; protein_id "ENSP00000329982.2"; transcript_support_level "NA"; hgnc_id "HGNC:15079"; tag "basic"; tag "appris_principal_1"; tag "CCDS"; ccdsid "CCDS41221.1"; havana_gene "OTTHUMG00000002581.3_2"; havana_transcript "OTTHUMT00000007334.3_2"; remap_original_location "chr1:-:685719-686654"; remap_status "full_contig";\n',
    # len(record["chrom"]) > 2
    'GL000193.1	HAVANA	gene	77815	78162	.	+	.	gene_id "ENSG00000279783.1_5"; gene_type "processed_pseudogene"; gene_name "AC018692.2"; level 2; havana_gene "OTTHUMG00000189459.1_5"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "new";\n',
]


class UpdateGencodeTest(TestCase):
    fixtures = ['users', 'reference_data']
    multi_db = True


    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.temp_file_path = os.path.join(self.test_dir, 'gencode.v31lift37.annotation.gtf.gz')
        with gzip.open(self.temp_file_path, 'w') as f:
            f.write(u''.join(GTF_DATA))

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        shutil.rmtree(self.test_dir)

    @mock.patch('os.path.isfile')
    def test_update_gencode_command_arguments(self, mock_isfile):
        # Test missing test required argument
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode')
        self.assertEqual(ce.exception.message, 'Error: argument --gencode-release is required')

        # Test required argument out-of-range
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=18')
        self.assertEqual(ce.exception.message, 'Error: argument --gencode-release: invalid choice: 18 (choose from 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31)')

        # Test genome_version out-of-range
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=19', '/var/tmp', '39')
        self.assertEqual(ce.exception.message, "Error: argument genome_version: invalid choice: u'39' (choose from '37', '38')")

        # Test missing genome_version when a GTF file is provided
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=19', '/var/tmp')
        self.assertEqual(ce.exception.message, "The genome version must also be specified after the gencode GTF file path")

        # Test gencode_release and genome_version mis-matched case 1
        mock_isfile.return_value = True
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=19', '/var/tmp.gz', '38')
        mock_isfile.assert_called_with('/var/tmp.gz')
        self.assertEqual(ce.exception.message, "Invalid genome_version: 38. gencode v19 only has a GRCh37 version")

        # Test gencode_release and genome_version mis-matched case 2
        mock_isfile.reset_mock()
        mock_isfile.return_value = True
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=20', '/var/tmp1.gz', '37')
        mock_isfile.assert_called_with('/var/tmp1.gz')
        self.assertEqual(ce.exception.message, "Invalid genome_version: 37. gencode v20, v21, v22 only have a GRCh38 version")

        # Test genome_version != 38 requires lifted data
        mock_isfile.reset_mock()
        mock_isfile.return_value = True
        with self.assertRaises(CommandError) as ce:
            call_command('update_gencode', '--gencode-release=23', '/var/tmp2.gz', '37')
        mock_isfile.assert_called_with('/var/tmp2.gz')
        self.assertEqual(ce.exception.message, "Invalid genome_version for file: /var/tmp2.gz. gencode v23 and up must have 'lift' in the filename or genome_version arg must be GRCh38")

    @mock.patch('reference_data.management.commands.update_gencode.logger')
    def test_update_gencode_command_bad_gtf_data(self, mock_logger):
        # Test wrong number data feilds in a line
        temp_bad_file_path = os.path.join(self.test_dir, 'bad.gencode.v23lift37.annotation.gtf.gz')
        with gzip.open(temp_bad_file_path, 'w') as f:
            f.write(u''.join(BAD_FIELDS_GTF_DATA))
        with self.assertRaises(ValueError) as ve:
            call_command('update_gencode', '--gencode-release=23', temp_bad_file_path, '37')
        self.assertEqual(ve.exception.message, 'Unexpected number of fields on line #0: [\'gene\', \'11869\', \'14412\', \'.\', \'+\', \'.\', \'gene_id "ENSG00000223972.4";\']')
        mock_logger.info.assert_called_with('Loading {} (genome version: 37)'.format(temp_bad_file_path))

    @mock.patch('reference_data.management.commands.update_gencode.logger')
    @mock.patch('reference_data.management.commands.update_gencode.download_file')
    def test_update_gencode_command_url_generation(self, mock_download, mock_logger):
        # Test the code paths of generating urls, gencode_release == 19
        mock_logger.reset_mock()
        mock_download.return_value = self.temp_file_path
        call_command('update_gencode', '--gencode-release=19')
        mock_download.assert_called_with("http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_19/gencode.v19.annotation.gtf.gz")

        # Test the code paths of generating urls, gencode_release <= 22
        mock_logger.reset_mock()
        call_command('update_gencode', '--gencode-release=20')
        mock_download.assert_called_with("http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_20/gencode.v20.annotation.gtf.gz")

        # Test the code paths of generating urls, gencode_release > 22
        mock_logger.reset_mock()
        mock_download.return_value = self.temp_file_path
        call_command('update_gencode', '--gencode-release=23')
        calls = [
            mock.call("http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_23/GRCh37_mapping/gencode.v23lift37.annotation.gtf.gz"),
            mock.call(
                "http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_23/gencode.v23.annotation.gtf.gz"),
        ]
        mock_download.assert_has_calls(calls)

    @mock.patch('reference_data.management.commands.update_gencode.logger')
    def test_update_gencode_command(self, mock_logger):
        # Test normal command function
        call_command('update_gencode', '--reset', '--gencode-release=31', self.temp_file_path, '37')
        calls = [
            mock.call('Dropping the 0 existing TranscriptInfo entries'),
            mock.call('Dropping the 49 existing GeneInfo entries'),
            mock.call(
                'Loading {} (genome version: 37)'.format(self.temp_file_path)),
            mock.call('Creating 2 GeneInfo records'),
            mock.call('Creating 2 TranscriptInfo records'),
            mock.call('Done'),
            mock.call('Stats: '),
            mock.call('  genes_created: 2'),
            mock.call('  transcripts_created: 2')
        ]
        mock_logger.info.assert_has_calls(calls)

        gene_infos = [{
            'start_grch37': gene.start_grch37,
            'chrom_grch37': gene.chrom_grch37,
            'coding_region_size_grch37': gene.coding_region_size_grch37,
            'gencode_release': gene.gencode_release,
            'gencode_gene_type': gene.gencode_gene_type,
            'gene_id': gene.gene_id,
            'gene_symbol': gene.gene_symbol,
            'end_grch37': gene.end_grch37,
            'strand_grch37': gene.strand_grch37
        } for gene in GeneInfo.objects.all()]
        self.assertEqual(len(gene_infos), 2)
        self.assertDictEqual(gene_infos[0], {'start_grch37': 11869, 'chrom_grch37': u'1', 'coding_region_size_grch37': 0, 'gencode_release': 31, 'gencode_gene_type': u'transcribed_unprocessed_pseudogene', 'gene_id': u'ENSG00000223972', 'gene_symbol': u'DDX11L1', 'end_grch37': 14409, 'strand_grch37': u'+'})
        self.assertDictEqual(gene_infos[1], {'start_grch37': 621059, 'chrom_grch37': u'1', 'coding_region_size_grch37': 936, 'gencode_release': 31, 'gencode_gene_type': u'protein_coding', 'gene_id': u'ENSG00000284662', 'gene_symbol': u'OR4F16', 'end_grch37': 622053, 'strand_grch37': u'-'})

        transcript_infos = {trans.transcript_id: {
            'start_grch37': trans.start_grch37,
            'end_grch37': trans.end_grch37,
            'strand_grch37': trans.strand_grch37,
            'chrom_grch37': trans.chrom_grch37,
            'gene_id': trans.gene.gene_id
        } for trans in TranscriptInfo.objects.all()}
        self.assertEqual(len(transcript_infos), 2)
        self.assertDictEqual(transcript_infos['ENST00000456328'], {'start_grch37': 11869, 'end_grch37': 14409, 'strand_grch37': u'+', 'chrom_grch37': u'1', 'gene_id': u'ENSG00000223972'})
        self.assertDictEqual(transcript_infos['ENST00000332831'], {'start_grch37': 621059, 'end_grch37': 622053, 'strand_grch37': u'-', 'chrom_grch37': u'1', 'gene_id': u'ENSG00000284662'})

        # Test normal command function without a --reset option
        mock_logger.reset_mock()
        call_command('update_gencode', '--gencode-release=31', self.temp_file_path, '37')
        calls = [
            mock.call(
                'Loading {} (genome version: 37)'.format(self.temp_file_path)),
            mock.call('Creating 0 GeneInfo records'),
            mock.call('Creating 0 TranscriptInfo records'),
            mock.call('Done'),
            mock.call('Stats: '),
            mock.call('  genes_skipped: 2'),
            mock.call('  transcripts_skipped: 2'),
            mock.call('  genes_created: 0'),
            mock.call('  transcripts_created: 0')
        ]
        mock_logger.info.assert_has_calls(calls)
