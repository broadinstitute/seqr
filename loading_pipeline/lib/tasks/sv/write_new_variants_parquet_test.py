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

TEST_SV_VCF = 'loading_pipeline/var/test/callsets/sv_1.vcf'
TEST_PEDIGREE_5 = 'loading_pipeline/var/test/pedigrees/test_pedigree_5.tsv'

TEST_GCNV_BED_FILE = 'loading_pipeline/var/test/callsets/gcnv_1.tsv'

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


def _write_existing_variants_parquet_fixture(
    variant_ids: list[str],
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    max_key_: int,
) -> None:
    n = len(variant_ids)
    path = existing_variants_parquet_path(reference_genome, dataset_type, TEST_RUN_ID)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame(
        {
            'variant_id': variant_ids,
            'key_': range(max_key_ - n + 1, max_key_ + 1),
        },
    ).to_parquet(path)


class WriteNewVariantsParquetTest(MockedReferenceDatasetsTestCase):
    @mock.patch(
        'loading_pipeline.lib.tasks.sv.write_new_variants_parquet.load_gencode_gene_symbol_to_gene_id',
    )
    def test_sv_write_new_variants_parquet_test(
        self,
        mock_load_gencode_gene_symbol_to_gene_id: Mock,
    ) -> None:
        mock_load_gencode_gene_symbol_to_gene_id.return_value = hl.dict(
            {'TAS1R1': 'ENSG00000173662'},
        )
        _write_existing_variants_parquet_fixture(
            EXISTING_SV_VARIANT_IDS,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            max_key_=726,
        )
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
                    'variantId': 'CPX_chr1_22',
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

    def test_gcnv_write_new_variants_parquet_test(
        self,
    ) -> None:
        _write_existing_variants_parquet_fixture(
            EXISTING_SV_VARIANT_IDS,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            max_key_=726,
        )
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.GCNV,
            SampleType.WES,
            'R0115_test_project2',
        )
        worker = luigi.worker.Worker()
        task = WriteNewSvVariantsParquetTask(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.GCNV,
            sample_type=SampleType.WES,
            callset_path=TEST_GCNV_BED_FILE,
            project_guids=[
                'R0115_test_project2',
            ],
            validations_to_skip=[ALL_VALIDATIONS],
            run_id=TEST_RUN_ID,
        )
        worker.add(task)
        worker.run()
        self.assertTrue(task.output().exists())
        self.assertTrue(task.complete())
        df = pd.read_parquet(
            new_variants_parquet_path(
                ReferenceGenome.GRCh38,
                DatasetType.GCNV,
                TEST_RUN_ID,
            ),
        )
        export_json = convert_ndarray_to_list(df.head(1).to_dict('records'))
        self.assertEqual(
            export_json,
            [
                {
                    'key': 0,
                    'xpos': 1100006937,
                    'chrom': '1',
                    'pos': 100006937,
                    'end': 100023213,
                    'rg37LocusEnd': {'contig': '1', 'position': 100488769},
                    'variantId': 'suffix_16456_DEL',
                    'liftedOverChrom': '1',
                    'liftedOverPos': 100472493,
                    'numExon': 3,
                    'svType': 'DEL',
                    'predictions': {'strvctvre': 0.5830000042915344},
                    'populations': {
                        'sv_callset': {
                            'ac': 1,
                            'af': 4.4014079321641475e-05,
                            'an': 22720,
                            'het': None,
                            'hom': None,
                        },
                    },
                    'sortedGeneConsequences': [
                        {'geneId': 'ENSG00000117620', 'majorConsequence': 'LOF'},
                        {'geneId': 'ENSG00000283761', 'majorConsequence': 'LOF'},
                        {'geneId': 'ENSG22222222222', 'majorConsequence': None},
                    ],
                },
            ],
        )
