import unittest
from unittest.mock import patch

from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.reference_data.updated_reference_dataset_parquet import (
    UpdatedReferenceDatasetParquetNoHailTask,
)

TEST_GNOMAD_SVS_VCF = (
    'loading_pipeline/var/test/reference_datasets/raw/gnomad_svs.vcf.gz'
)


class GnomadSVsTest(unittest.TestCase):
    @patch.object(ReferenceDataset, 'path')
    def test_gnomad_svs(self, mock_path):
        mock_path.return_value = TEST_GNOMAD_SVS_VCF
        df = UpdatedReferenceDatasetParquetNoHailTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SV,
            reference_dataset=ReferenceDataset.gnomad_svs,
            run_id='manual__2024-04-03',
            attempt_id=1,
        ).create_data_frame()
        self.assertEqual(
            df.to_dict('records'),
            [
                {
                    'ID': 'gnomAD-SV_v3_BND_chr1_1a45f73a',
                    '#CHROM': 'chr1',
                    'POS': 10434,
                    'SVTYPE': 'BND',
                    'END': 10434.0,
                    'SVLEN': -1.0,
                    'af': 0.114134,
                    'ac': 8474.0,
                    'an': 74246.0,
                    'het': 8426.0,
                    'hom': 24.0,
                },
                {
                    'ID': 'gnomAD-SV_v3_BND_chr1_3fa36917',
                    '#CHROM': 'chr1',
                    'POS': 10440,
                    'SVTYPE': 'BND',
                    'END': 10440.0,
                    'SVLEN': -1.0,
                    'af': 0.004201,
                    'ac': 466.0,
                    'an': 110936.0,
                    'het': 466.0,
                    'hom': 0.0,
                },
                {
                    'ID': 'gnomAD-SV_v3_BND_chr1_7bbf34b5',
                    '#CHROM': 'chr1',
                    'POS': 10464,
                    'SVTYPE': 'BND',
                    'END': 10464.0,
                    'SVLEN': -1.0,
                    'af': 0.036985,
                    'ac': 3119.0,
                    'an': 84332.0,
                    'het': 3115.0,
                    'hom': 2.0,
                },
                {
                    'ID': 'gnomAD-SV_v3_BND_chr1_933a2971',
                    '#CHROM': 'chr1',
                    'POS': 10450,
                    'SVTYPE': 'BND',
                    'END': 10450.0,
                    'SVLEN': -1.0,
                    'af': 0.323899,
                    'ac': 21766.0,
                    'an': 67200.0,
                    'het': 21616.0,
                    'hom': 75.0,
                },
                {
                    'ID': 'gnomAD-SV_v3_DUP_chr1_01c2781c',
                    '#CHROM': 'chr1',
                    'POS': 10000,
                    'SVTYPE': 'DUP',
                    'END': 295666.0,
                    'SVLEN': 285666.0,
                    'af': 0.001997,
                    'ac': 139.0,
                    'an': 69594.0,
                    'het': 139.0,
                    'hom': 0.0,
                },
            ],
        )
