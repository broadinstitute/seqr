import mock
import __builtin__

from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError

from reference_data.models import GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38

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

    @mock.patch('os.path.isfile')
    @mock.patch('reference_data.management.commands.update_gencode.logger')
    @mock.patch('reference_data.management.commands.update_gencode.download_file')
    @mock.patch('reference_data.management.commands.update_gencode.tqdm')
    @mock.patch('gzip.open')
    def test_update_gencode_command_special_paths(self, mock_gzip_open, mock_tqdm, mock_download, mock_logger, mock_isfile):
        # Test --reset option and wrong number data feilds in a line
        gtf_path = '/var/gencode.v31lift37.annotation.gtf.gz'
        mock_isfile.return_value = True
        mock_file = mock_gzip_open.return_value.__enter__.return_value
        mock_tqdm.return_value = BAD_FIELDS_GTF_DATA
        with self.assertRaises(ValueError) as ve:
            call_command('update_gencode', '--reset', '--gencode-release=23', gtf_path, '37')
        mock_isfile.assert_called_with(gtf_path)
        self.assertEqual(ve.exception.message, 'Unexpected number of fields on line #0: [\'gene\', \'11869\', \'14412\', \'.\', \'+\', \'.\', \'gene_id "ENSG00000223972.4";\']')
        mock_gzip_open.assert_called_with(gtf_path)
        mock_tqdm.assert_called_with(mock_file, unit=' gencode records')
        mock_logger.info.assert_called_with('Loading /var/gencode.v31lift37.annotation.gtf.gz (genome version: 37)')

        # Test generating urls, gencode_release == 19
        mock_logger.reset_mock()
        mock_gzip_open.reset_mock()
        mock_download.return_value = '/var/downloaded_file.gz'
        with self.assertRaises(ValueError) as ve:
            call_command('update_gencode', '--gencode-release=19')
        mock_download.assert_called_with("http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_19/gencode.v19.annotation.gtf.gz")
        mock_gzip_open.assert_called_with('/var/downloaded_file.gz')
        mock_logger.info.assert_called_with('Loading /var/downloaded_file.gz (genome version: 37)')

        # Test generating urls, gencode_release <= 22
        mock_logger.reset_mock()
        mock_gzip_open.reset_mock()
        mock_download.reset_mock()
        mock_download.return_value = '/var/downloaded_file.gz'
        with self.assertRaises(ValueError) as ve:
            call_command('update_gencode', '--gencode-release=20')
        mock_download.assert_called_with("http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_20/gencode.v20.annotation.gtf.gz")
        mock_gzip_open.assert_called_with('/var/downloaded_file.gz')
        mock_logger.info.assert_called_with('Loading /var/downloaded_file.gz (genome version: 38)')

        # test generating urls, gencode_release > 22
        mock_logger.reset_mock()
        mock_download.reset_mock()
        mock_gzip_open.reset_mock()
        mock_download.side_effect = ['/var/downloaded_file37.gz', '/var/downloaded_file38.gz']
        mock_tqdm.side_effect = [[], BAD_FIELDS_GTF_DATA]
        with self.assertRaises(ValueError) as ve:
            call_command('update_gencode', '--gencode-release=23')
        calls = [
            mock.call("http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_23/GRCh37_mapping/gencode.v23lift37.annotation.gtf.gz"),
            mock.call(
                "http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_23/gencode.v23.annotation.gtf.gz"),
        ]
        mock_download.assert_has_calls(calls)
        calls = [
            mock.call('/var/downloaded_file37.gz'),
            mock.call('/var/downloaded_file38.gz'),
        ]
        mock_gzip_open.assert_has_calls(calls, any_order = True)
        calls = [
            mock.call('Loading /var/downloaded_file38.gz (genome version: 38)'),
            mock.call('Loading /var/downloaded_file37.gz (genome version: 37)'),
        ]
        mock_logger.info.assert_has_calls(calls, any_order = True)

    @mock.patch('os.path.isfile')
    @mock.patch('reference_data.management.commands.update_gencode.logger')
    @mock.patch('reference_data.management.commands.update_gencode.tqdm')
    @mock.patch('gzip.open')
    def test_update_gencode_command(self, mock_gzip_open, mock_tqdm, mock_logger, mock_isfile):
        # Test normal command function
        mock_isfile.return_value = True
        mock_file = mock_gzip_open.return_value.__enter__.return_value
        mock_tqdm.return_value = GTF_DATA
        gtf_path = '/var/folders/p8/c2yjwplx5n5c8z8s5c91ddqc0000gq/T/gencode.v31lift37.annotation.gtf.gz'
        call_command('update_gencode', '--gencode-release=31', gtf_path, '37')

        mock_gzip_open.assert_called_with(gtf_path)
        mock_tqdm.assert_called_with(mock_file, unit=' gencode records')
        mock_isfile.assert_called_with(gtf_path)

        calls = [
            mock.call(
                'Loading /var/folders/p8/c2yjwplx5n5c8z8s5c91ddqc0000gq/T/gencode.v31lift37.annotation.gtf.gz (genome version: 37)'),
            mock.call('Creating 1 GeneInfo records'),
            mock.call('Creating 2 TranscriptInfo records'),
            mock.call('Done'),
            mock.call('Stats: '),
            mock.call('  genes_skipped: 1'),
            mock.call('  genes_created: 1'),
            mock.call('  transcripts_created: 2')
        ]
        mock_logger.info.assert_has_calls(calls)
