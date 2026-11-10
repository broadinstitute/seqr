import gzip
import unittest

import responses

from loading_pipeline.lib.reference_datasets.gencode.mapping_gene_ids import (
    GENCODE_ENSEMBL_TO_REFSEQ_URL,
    load_gencode_ensembl_to_refseq_id,
)


ENSEMBL_TO_REFSEQ_DATA = b"""ENST00000424215.1\tNR_121638.1
ENST00000378391.6\tNM_199454.3\tNP_955533.2
ENST00000270722.10\tNM_022114.4\tNP_071397.3
ENST00000288774.8\tNM_001374425.1\tNP_001361354.1"""


class LoadGencodeTestCase(unittest.TestCase):
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
