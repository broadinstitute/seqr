import mock
import responses
import gzip

from django.core.management import call_command

from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase
from reference_data.models import GeneInfo, TranscriptInfo, RefseqTranscript, DataVersions

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
    'ENST00000332831.1	NR_122045.1	\n',
    'ENST00000342066.8	NM_152486.3	NP_689699.2\n',
]


class UpdateGencodeTest(ReferenceDataCommandTestCase):

    def setUp(self):
        super().setUp()

        patcher = mock.patch('seqr.views.utils.export_utils.open')
        self.mock_open = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
        self.mock_temp_dir = patcher.start()
        self.mock_temp_dir.return_value.__enter__.return_value = self.tmp_dir
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.subprocess.Popen')
        self.mock_subprocess = patcher.start()
        self.mock_subprocess.return_value.wait.return_value = 0
        self.addCleanup(patcher.stop)

        self.gzipped_gtf_data = gzip.compress(''.join(GTF_DATA).encode())
        self._add_latest_responses()

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
        self.assertEqual(trans_info.refseqtranscript.refseq_id, 'NM_015658.4')
        trans_info = TranscriptInfo.objects.get(transcript_id='ENST00000332831')
        self.assertEqual(trans_info.start_grch37, 621059)
        self.assertEqual(trans_info.end_grch37, 622053)
        self.assertEqual(trans_info.strand_grch37, '-')
        self.assertEqual(trans_info.chrom_grch37, '1')
        self.assertEqual(trans_info.gene.gene_id, 'ENSG00000284662')
        self.assertEqual(trans_info.gene.gencode_release, 39)
        self.assertTrue(trans_info.is_mane_select)
        self.assertEqual(trans_info.refseqtranscript.refseq_id, 'NR_122045.1')

    def _add_latest_responses(self):
        url = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/gencode.v39.annotation.gtf.gz'
        responses.add(responses.HEAD, url, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url, body=self.gzipped_gtf_data, stream=True)
        url_lift = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/GRCh37_mapping/gencode.v39lift37.annotation.gtf.gz'
        responses.add(responses.HEAD, url_lift, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url_lift, body=self.gzipped_gtf_data, stream=True)
        url_refseq = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/gencode.v39.metadata.RefSeq.gz'
        responses.add(responses.GET, url_refseq, body=gzip.compress(''.join(REFSEQ_DATA).encode()))
        return url, url_lift

    @responses.activate
    def test_load_all_gencode_command(self):
        GeneInfo.objects.all().delete()
        DataVersions.objects.get(data_model_name='GeneInfo').delete()

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
        call_command('update_all_reference_data')

        skipped_logs = [
            mock.call('genes_skipped: 4'),
            mock.call('transcripts_skipped: 4'),
        ]
        self.mock_logger.info.assert_has_calls([
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v39lift37.annotation.gtf.gz'),
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v39.annotation.gtf.gz'),
            mock.call('Created 2 GeneInfo records'),
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v31lift37.annotation.gtf.gz'),
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v31.annotation.gtf.gz'),
        ] + skipped_logs + [
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v29lift37.annotation.gtf.gz'),
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v29.annotation.gtf.gz'),
        ] + skipped_logs + [
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v28lift37.annotation.gtf.gz'),
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v28.annotation.gtf.gz'),
        ] + skipped_logs + [
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v27lift37.annotation.gtf.gz'),
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v27.annotation.gtf.gz'),
        ] + skipped_logs + [
            mock.call(f'Parsing file {self.tmp_dir }/gencode.v19.annotation.gtf.gz'),
            mock.call('genes_skipped: 2'),
            mock.call('transcripts_skipped: 2'),
            mock.call('Created 1 GeneInfo records'),
            mock.call('Created 3 TranscriptInfo records'),
            mock.call('Updating RefseqTranscript'),
            mock.call(f'Parsing file {self.tmp_dir}/gencode.v39.metadata.RefSeq.gz'),
            mock.call('Deleted 0 RefseqTranscript records'),
            mock.call('Created 2 RefseqTranscript records'),
            mock.call('Done'),
            mock.call('Loaded 2 RefseqTranscript records'),
            mock.call('Skipped 2 records with unrecognized or duplicated transcripts'),
        ])
        self.mock_subprocess.assert_not_called()

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
    def test_update_gencode_latest_command(self):
        # Test only update the latest version
        dv = DataVersions.objects.get(data_model_name='GeneInfo')
        dv.version = '31'
        dv.save()

        call_command('update_all_reference_data', '--gene-symbol-change-dir', 'gs://seqr-reference-data/gencode')
        self.mock_command_logger.info.assert_has_calls([
            mock.call('Dropped 1 existing TranscriptInfo records'),
            mock.call('Done'),
            mock.call('Updated: GeneInfo'),
        ])
        self.mock_logger.info.assert_has_calls([
            mock.call(f'Parsing file {self.tmp_dir}/gencode.v39lift37.annotation.gtf.gz'),
            mock.call(f'Parsing file {self.tmp_dir}/gencode.v39.annotation.gtf.gz'),
            mock.call('Updated 1 previously loaded GeneInfo records'),
            mock.call('Created 1 GeneInfo records'),
            mock.call('Created 2 TranscriptInfo records'),
            mock.call('Updating RefseqTranscript'),
            mock.call(f'Parsing file {self.tmp_dir}/gencode.v39.metadata.RefSeq.gz'),
            mock.call('Deleted 1 RefseqTranscript records'),
            mock.call('Created 3 RefseqTranscript records'),
            mock.call('Done'),
        ])

        self._has_expected_new_genes()

        self.assertEqual(TranscriptInfo.objects.all().count(), 3)
        self._has_expected_new_transcripts()

        self.assertEqual(RefseqTranscript.objects.count(), 3)
        self.assertEqual(
            RefseqTranscript.objects.get(transcript__transcript_id='ENST00000258436').refseq_id, 'NR_026874.2',
        )

        self.mock_subprocess.assert_called_with(
            f'gsutil mv {self.tmp_dir}/* gs://seqr-reference-data/gencode/', stdout=-1, stderr=-2, shell=True,  # nosec
        )
        self.mock_open.assert_called_with(f'{self.tmp_dir}/gene_symbol_changes__39.csv', 'w')
        self.assertEqual(
            self.mock_open.return_value.__enter__.return_value.write.call_args.args[0],
            'gene_id,old_symbol,new_symbol\nENSG00000223972,DDX11L1,DDX11L1A',
        )
