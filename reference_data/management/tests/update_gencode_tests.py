import mock
import os
import responses
import tempfile
import shutil
import gzip

from django.core.management import call_command
from django.test import TestCase

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

ADDITIONAL_GTF_DATA = [
    'chr1	HAVANA	gene	367640	368634	.	-	.	gene_id "ENSG00000235249.1_2"; gene_type "protein_coding"; gene_name "OR4F29"; level 2; hgnc_id "HGNC:15079"; havana_gene "OTTHUMG00000002581.3_2"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "overlap";\n',
    'chr1	HAVANA	transcript	367640	368634	.	-	.	gene_id "ENSG00000235249.1_2"; transcript_id "ENST00000235249.4_2"; '
    'gene_type "protein_coding"; gene_name "OR4F16"; transcript_type "protein_coding"; transcript_name "OR4F16-201"; level 2; '
    'protein_id "ENSP00000329982.2"; transcript_support_level "NA"; hgnc_id "HGNC:15079"; tag "basic"; tag "MANE_Select"; tag "CCDS"; '
    'ccdsid "CCDS41221.1"; havana_gene "OTTHUMG00000002581.3_2"; havana_transcript "OTTHUMT00000007334.3_2"; remap_num_mappings 1; '
    'remap_status "full_contig"; remap_target_status "overlap";\n',
    'chr1	HAVANA	CDS	367640	368634	.	-	0	gene_id "ENSG00000235249.1_2"; transcript_id "ENST00000235249.4_2"; gene_type "protein_coding"; gene_name "OR4F29"; transcript_type "protein_coding"; transcript_name "OR4F16-201"; exon_number 1; exon_id "ENSE00002324228.3"; level 2; protein_id "ENSP00000329982.2"; transcript_support_level "NA"; hgnc_id "HGNC:15079"; tag "basic"; tag "appris_principal_1"; tag "CCDS"; ccdsid "CCDS41221.1"; havana_gene "OTTHUMG00000002581.3_2"; havana_transcript "OTTHUMT00000007334.3_2"; remap_original_location "chr1:-:685719-686654"; remap_status "full_contig";\n',
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
        self.test_dirname = os.path.dirname(self.test_dir)
        self.gzipped_gtf_data = gzip.compress(''.join(GTF_DATA).encode())
        self._add_latest_responses()

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        shutil.rmtree(self.test_dir)

    @responses.activate
    @mock.patch('reference_data.models.logger')
    def test_update_gencode_command_bad_gtf_data(self, mock_logger):
        # Test wrong number data feilds in a line
        bad_gtf_data = gzip.compress(''.join(BAD_FIELDS_GTF_DATA).encode())
        url = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/GRCh37_mapping/gencode.v39lift37.annotation.gtf.gz'
        responses.replace(responses.GET, url, body=bad_gtf_data, stream=True)

        with self.assertRaises(ValueError) as ve:
            call_command('update_gencode_latest')
        self.assertIn(str(ve.exception), ['Unexpected number of fields on line #0: [\'gene\', \'11869\', \'14412\', \'.\', \'+\', \'.\', \'gene_id "ENSG00000223972.4";\']',
                                          'Unexpected number of fields on line #0: [u\'gene\', u\'11869\', u\'14412\', u\'.\', u\'+\', u\'.\', u\'gene_id "ENSG00000223972.4";\']'])
        mock_logger.info.assert_called_with(f'Loading {self.test_dirname}/gencode.v39lift37.annotation.gtf.gz (genome version: 37)')

    def _has_expected_new_genes(self):
        gene_info = GeneInfo.objects.get(gene_id='ENSG00000223972')
        self.assertEqual(gene_info.gencode_release, 39)
        gene_info = GeneInfo.objects.get(gene_id='ENSG00000284662')
        self.assertEqual(gene_info.start_grch37, 621059)
        self.assertEqual(gene_info.chrom_grch37, '1')
        self.assertEqual(gene_info.coding_region_size_grch37, 936)
        self.assertEqual(gene_info.gencode_release, 39)
        self.assertEqual(gene_info.gencode_gene_type, 'protein_coding')
        self.assertEqual(gene_info.gene_symbol, 'OR4F16')

    def _has_expected_new_transcripts(self):
        trans_info = TranscriptInfo.objects.get(transcript_id='ENST00000624735')
        self.assertEqual(trans_info.gene.gene_id, 'ENSG00000223972')
        self.assertEqual(trans_info.gene.gencode_release, 39)
        self.assertFalse(trans_info.is_mane_select)
        trans_info = TranscriptInfo.objects.get(transcript_id='ENST00000332831')
        self.assertEqual(trans_info.start_grch37, 621059)
        self.assertEqual(trans_info.end_grch37, 622053)
        self.assertEqual(trans_info.strand_grch37, '-')
        self.assertEqual(trans_info.chrom_grch37, '1')
        self.assertEqual(trans_info.gene.gene_id, 'ENSG00000284662')
        self.assertEqual(trans_info.gene.gencode_release, 39)
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
    @mock.patch('reference_data.models.logger')
    @mock.patch('reference_data.management.commands.update_gencode_latest.logger')
    def test_load_all_gencode_command(self, mock_logger, mock_utils_logger):
        # Initial gencode loading can only happen once with an empty gene table
        GeneInfo.objects.all().delete()

        for version in [27, 28, 29, 31]:
            url = f'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{version}/gencode.v{version}.annotation.gtf.gz'
            responses.add(responses.HEAD, url, headers={"Content-Length": "1024"})
            responses.add(responses.GET, url, body=self.gzipped_gtf_data, stream=True)
            url_lift = f'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{version}/GRCh37_mapping/gencode.v{version}lift37.annotation.gtf.gz'
            responses.add(responses.HEAD, url_lift, headers={"Content-Length": "1024"})
            responses.add(responses.GET, url_lift, body=self.gzipped_gtf_data, stream=True)

        additional_gtf_data = gzip.compress(''.join(GTF_DATA + ADDITIONAL_GTF_DATA).encode())
        url_19 = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_19/gencode.v19.annotation.gtf.gz'
        responses.add(responses.HEAD, url_19, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url_19, body=additional_gtf_data, stream=True)

        # Test initial load for all gencode data
        call_command(
            'update_all_reference_data', '--skip-omim', '--skip-dbnsfp-gene', '--skip-gene-constraint',
            '--skip-primate-ai', '--skip-mgi', '--skip-hpo', '--skip-gene-cn-sensitivity', '--skip-gencc',
            '--skip-clingen', '--skip-refseq',
        )

        mock_utils_logger.info.assert_has_calls([
            mock.call(f'Loading {self.test_dirname }/gencode.v39lift37.annotation.gtf.gz (genome version: 37)'),
            mock.call(f'Loading {self.test_dirname }/gencode.v39.annotation.gtf.gz (genome version: 38)'),
            mock.call('Creating 2 TranscriptInfo records'),
            mock.call(f'Loading {self.test_dirname }/gencode.v31lift37.annotation.gtf.gz (genome version: 37)'),
            mock.call(f'Loading {self.test_dirname }/gencode.v31.annotation.gtf.gz (genome version: 38)'),
            mock.call(f'Loading {self.test_dirname }/gencode.v29lift37.annotation.gtf.gz (genome version: 37)'),
            mock.call(f'Loading {self.test_dirname }/gencode.v29.annotation.gtf.gz (genome version: 38)'),
            mock.call(f'Loading {self.test_dirname }/gencode.v28lift37.annotation.gtf.gz (genome version: 37)'),
            mock.call(f'Loading {self.test_dirname }/gencode.v28.annotation.gtf.gz (genome version: 38)'),
            mock.call(f'Loading {self.test_dirname }/gencode.v27lift37.annotation.gtf.gz (genome version: 37)'),
            mock.call(f'Loading {self.test_dirname }/gencode.v27.annotation.gtf.gz (genome version: 38)'),
            mock.call(f'Loading {self.test_dirname }/gencode.v19.annotation.gtf.gz (genome version: 37)'),
            mock.call('Creating 1 TranscriptInfo records'),
        ])
        all_skipped_logs = [
            mock.call('Done'),
            mock.call('Stats: '),
            mock.call('  genes_skipped: 4'),
            mock.call('  transcripts_skipped: 4'),
        ]
        calls = [
            mock.call('Creating 2 GeneInfo records'),
            mock.call('Done'),
            mock.call('Stats: '),
            mock.call('  genes_created: 2'),
            mock.call('  transcripts_created: 2'),
        ] + all_skipped_logs * 4 + [
            mock.call('Creating 1 GeneInfo records'),
            mock.call('Done'),
            mock.call('Stats: '),
            mock.call('  genes_skipped: 2'),
            mock.call('  transcripts_skipped: 2'),
            mock.call('  genes_created: 1'),
            mock.call('  transcripts_created: 1')
        ]
        mock_logger.info.assert_has_calls(calls)

        self._has_expected_new_genes()
        gene_info = GeneInfo.objects.get(gene_id='ENSG00000235249')
        self.assertEqual(gene_info.gencode_release, 19)
        self.assertEqual(gene_info.start_grch37, 367640)
        self.assertEqual(gene_info.end_grch37, 368634)
        self.assertEqual(gene_info.chrom_grch37, '1')
        self.assertEqual(gene_info.coding_region_size_grch37, 995)
        self.assertIsNone(gene_info.start_grch38)
        self.assertEqual(gene_info.coding_region_size_grch38, 0)

        self.assertEqual(TranscriptInfo.objects.all().count(), 3)
        self._has_expected_new_transcripts()
        trans_info = TranscriptInfo.objects.get(transcript_id='ENST00000235249')
        self.assertEqual(trans_info.gene.gene_id, 'ENSG00000235249')
        self.assertEqual(trans_info.gene.gencode_release, 19)

    @responses.activate
    @mock.patch('reference_data.models.logger')
    @mock.patch('reference_data.management.commands.update_gencode_latest.logger')
    def test_update_gencode_latest_command(self, mock_command_logger, mock_logger):
        refseq_url = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/gencode.v39.metadata.RefSeq.gz'
        responses.add(responses.HEAD, refseq_url, headers={"Content-Length": "1024"})
        responses.add(responses.GET, refseq_url, body=gzip.compress(''.join(REFSEQ_DATA).encode()))

        call_command('update_gencode_latest', '--track-symbol-change', f'--output-dir={self.test_dir}')
        mock_command_logger.info.assert_called_with('Dropped 1 existing TranscriptInfo records')
        mock_logger.info.assert_has_calls([
            mock.call(f'Parsing file {self.test_dirname}/gencode.v39lift37.annotation.gtf.gz'),
            mock.call(f'Parsing file {self.test_dirname}/gencode.v39.annotation.gtf.gz'),
            mock.call('Updated 1 previously loaded GeneInfo records'),
            mock.call('Created 1 GeneInfo records'),
            mock.call('Created 2 TranscriptInfo records'),
            mock.call('Updating RefseqTranscript'),
            mock.call(f'Parsing file {self.test_dirname}/gencode.v39.metadata.RefSeq.gz'),
            mock.call('Deleted 1 RefseqTranscript records'),
            mock.call('Created 2 RefseqTranscript records'),
            mock.call('Done'),
        ])

        self._has_expected_new_genes()

        self.assertEqual(TranscriptInfo.objects.all().count(), 3)
        self._has_expected_new_transcripts()

        self.assertEqual(RefseqTranscript.objects.count(), 2)
        self.assertListEqual(
            list(RefseqTranscript.objects.order_by('transcript_id').values('transcript__transcript_id', 'refseq_id')), [
                {'transcript__transcript_id': 'ENST00000258436', 'refseq_id': 'NR_026874.2'},
                {'transcript__transcript_id': 'ENST00000624735', 'refseq_id': 'NM_015658.4'}
            ])

        with open(f'{self.test_dir}/gene_symbol_changes.csv') as f:
            self.assertListEqual(f.readlines(), ['ENSG00000223972,DDX11L1,DDX11L1A\n'])
