import os
from unittest import mock
from unittest.mock import Mock

import hail as hl
import luigi.worker
import pandas as pd

from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.misc.validation import ALL_VALIDATIONS
from loading_pipeline.lib.paths import (
    existing_variants_parquet_path,
    new_variants_parquet_path,
)
from loading_pipeline.lib.tasks.sv.write_new_variants_parquet import (
    WriteNewSvVariantsParquetTask,
)
from loading_pipeline.lib.test.misc import (
    convert_ndarray_to_list,
    copy_project_pedigree_to_mocked_dir,
)
from loading_pipeline.lib.test.mocked_reference_datasets_testcase import (
    MockedReferenceDatasetsTestCase,
)

TEST_SV_VCF = 'loading_pipeline/var/test/callsets/sv_1/*.vcf.gz'
TEST_PEDIGREE_5 = 'loading_pipeline/var/test/pedigrees/test_pedigree_5.tsv'

TEST_RUN_ID = 'manual__2024-04-03'

EXISTING_SV_VARIANT_IDS = [
    'BND_chr1_6',
    'DUP_chr1_5',
    'DEL_chr1_12',
    'BND_chr1_9',
    'INS_chr1_65',
    'CPX_chr1_41',
    'INS_chr1_268',
    'CPX_chr1_54',
    'INS_chr1_688',
    'CPX_chr1_251',
    'CPX_chrX_251',
    'CPX_chrX_252',
]


def _write_existing_variants_parquet_fixture() -> None:
    n = len(EXISTING_SV_VARIANT_IDS)
    path = existing_variants_parquet_path(
        ReferenceGenome.GRCh38,
        DatasetType.SV,
        TEST_RUN_ID,
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame(
        {
            'variant_id': EXISTING_SV_VARIANT_IDS,
            'key_': range(727 - n, 727),
            'chrom': [b'1'] * (n - 2) + [b'X'] * 2,
            'end': [
                20404,
                263666,
                428500,
                789481,
                4228448,
                16089601,
                17465723,
                21480419,
                48963135,
                181074952,
                2781000,
                2781900,
            ],
            'endChrom': [b'5'] + [None] * (n - 1),
            'pos': [
                180928,
                257666,
                413968,
                789481,
                4228405,
                16088760,
                17465707,
                21427498,
                48963084,
                180540234,
                3,
                2781700,
            ],
            'svType': [
                b'BND',
                b'DUP',
                b'DEL',
                b'BND',
                b'INS',
                b'CPX',
                b'INS',
                b'CPX',
                b'INS',
                b'CPX',
                b'CPX',
                b'CPX',
            ],
        },
    ).to_parquet(path)


class WriteNewVariantsParquetTest(MockedReferenceDatasetsTestCase):
    @mock.patch(
        'loading_pipeline.lib.tasks.sv.single_sample_vcf.random',
    )
    @mock.patch(
        'loading_pipeline.lib.tasks.sv.write_new_variants_parquet.load_gencode_gene_symbol_to_gene_id',
    )
    def test_sv_write_new_variants_parquet_test(
        self,
        mock_load_gencode_gene_symbol_to_gene_id: Mock,
        mock_random: Mock,
    ) -> None:
        mock_load_gencode_gene_symbol_to_gene_id.return_value = hl.dict(
            {'TAS1R1': 'ENSG00000173662'},
        )
        mock_random.randint.side_effect = range(1, 10)
        _write_existing_variants_parquet_fixture()
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            'R0115_test_project2',
        )
        worker = luigi.worker.Worker()
        task = WriteNewSvVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SV,
            sample_type=SampleType.WGS,
            callset_path=TEST_SV_VCF,
            project_guids=[
                'R0115_test_project2',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
            skip_expect_tdr_metrics=True,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        df = pd.read_parquet(
            new_variants_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.SV,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.head(1).to_dict('records'))
        export_json[0]['sortedGeneConsequences'] = [
            export_json[0]['sortedGeneConsequences'][0],
        ]
        self.maxDiff = None
        self.assertEqual(
            export_json,
            [
                {
                    'key': 727,
                    'xpos': 1006558902,
                    'chrom': '1',
                    'pos': 6558902,
                    'end': 6559723,
                    'rg37LocusEnd': {'contig': '1', 'position': 6619783},
                    'variantId': 'CPX_chr1_22_1',
                    'liftedOverChrom': '1',
                    'liftedOverPos': 6618962,
                    'algorithms': 'manta',
                    'bothsidesSupport': True,
                    'cpxIntervals': [
                        {'chrom': '1', 'start': 6558902, 'end': 6559723, 'type': 'INV'},
                        {'chrom': '1', 'start': 6559655, 'end': 6559723, 'type': 'DUP'},
                    ],
                    'endChrom': None,
                    'svSourceDetail': None,
                    'svType': 'CPX',
                    'svTypeDetail': 'INVdup',
                    'predictions': {'strvctvre': None},
                    'populations': {'gnomad_svs': None},
                    'sortedGeneConsequences': [
                        {'geneId': 'ENSG00000173662', 'majorConsequence': 'INTRONIC'},
                    ],
                },
            ],
        )
