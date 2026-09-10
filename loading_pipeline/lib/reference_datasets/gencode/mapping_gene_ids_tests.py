import gzip
import unittest

import responses

from loading_pipeline.lib.reference_datasets.gencode.mapping_gene_ids import (
    GENCODE_ENSEMBL_TO_REFSEQ_URL,
    GENCODE_GTF_URL,
    load_gencode_ensembl_to_refseq_id,
    load_gencode_gene_symbol_to_gene_id,
)

GTF_DATA = [
    '#description: evidence-based annotation of the human genome, version 31 (Ensembl 97), mapped to GRCh37 with gencode-backmap',
    'chr1	HAVANA	gene	11869	14409	.	+	.	gene_id "ENSG00000223972.5_2"; gene_type "transcribed_unprocessed_pseudogene"; gene_name "DDX11L1"; level 2; hgnc_id "HGNC:37102"; havana_gene "OTTHUMG00000000961.2_2"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "overlap";',
    'chr1	HAVANA	gene	621059	622053	.	-	.	gene_id "ENSG00000284662.1_2"; gene_type "protein_coding"; gene_name "OR4F16"; level 2; hgnc_id "HGNC:15079"; havana_gene "OTTHUMG00000002581.3_2"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "overlap";',
    'GL000193.1	HAVANA	gene	77815	78162	.	+	.	gene_id "ENSG00000279783.1_5"; gene_type "processed_pseudogene"; gene_name "AC018692.2"; level 2; havana_gene "OTTHUMG00000189459.1_5"; remap_status "full_contig"; remap_num_mappings 1; remap_target_status "new";',
]
GENE_ID_MAPPING = {
    'DDX11L1': 'ENSG00000223972',
    'OR4F16': 'ENSG00000284662',
    'AC018692.2': 'ENSG00000279783',
}


ENSEMBL_TO_REFSEQ_DATA = b"""ENST00000424215.1\tNR_121638.1
ENST00000378391.6\tNM_199454.3\tNP_955533.2
ENST00000270722.10\tNM_022114.4\tNP_071397.3
ENST00000288774.8\tNM_001374425.1\tNP_001361354.1"""


class LoadGencodeTestCase(unittest.TestCase):
    @responses.activate
    def test_load_gencode_gene_symbol_to_gene_id(self):
        url = GENCODE_GTF_URL.format(gencode_release=12)
        responses.add(
            responses.GET,
            url,
            body=gzip.compress(('\n'.join(GTF_DATA)).encode()),
        )
        mapping = load_gencode_gene_symbol_to_gene_id(12)
        self.assertDictEqual(
            mapping,
            {
                'AC018692.2': 'ENSG00000279783',
                'DDX11L1': 'ENSG00000223972',
                'OR4F16': 'ENSG00000284662',
            },
        )

    @responses.activate
    def test_load_gencode_ensembl_to_refseq_id(self):
        url = GENCODE_ENSEMBL_TO_REFSEQ_URL.format(gencode_release=20)
        responses.add(responses.GET, url, body=gzip.compress(ENSEMBL_TO_REFSEQ_DATA))
        mapping = load_gencode_ensembl_to_refseq_id(20)
        self.assertDictEqual(
            mapping,
            {
                'ENST00000424215': 'NR_121638.1',
                'ENST00000378391': 'NM_199454.3',
                'ENST00000270722': 'NM_022114.4',
                'ENST00000288774': 'NM_001374425.1',
            },
        )
