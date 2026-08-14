import gzip
from unittest.mock import Mock, patch

import hailtop.fs as hfs
import luigi.worker

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.misc.validation import ALL_VALIDATIONS
from loading_pipeline.lib.tasks.update_variant_annotations_table_with_new_variants import (
    UpdateVariantAnnotationsTableWithNewVariantsTask,
)
from loading_pipeline.lib.tasks.write_variant_annotations_vcf import (
    WriteVariantAnnotationsVCF,
)
from loading_pipeline.lib.test.misc import copy_project_pedigree_to_mocked_dir
from loading_pipeline.lib.test.mocked_reference_datasets_testcase import (
    MockedReferenceDatasetsTestCase,
)

TEST_SV_VCF = 'loading_pipeline/var/test/callsets/sv_1.vcf'
TEST_PEDIGREE_5 = 'loading_pipeline/var/test/pedigrees/test_pedigree_5.tsv'

GENE_ID_MAPPING = {
    'OR4F5': 'ENSG00000186092',
    'PLEKHG4B': 'ENSG00000153404',
    'OR4F16': 'ENSG00000186192',
    'OR4F29': 'ENSG00000284733',
    'FBXO28': 'ENSG00000143756',
    'SAMD11': 'ENSG00000187634',
    'C1orf174': 'ENSG00000198912',
    'TAS1R1': 'ENSG00000173662',
    'FAM131C': 'ENSG00000185519',
    'RCC2': 'ENSG00000179051',
    'NBPF3': 'ENSG00000142794',
    'AGBL4': 'ENSG00000186094',
    'KIAA1614': 'ENSG00000135835',
    'MR1': 'ENSG00000153029',
    'STX6': 'ENSG00000135823',
    'XPR1': 'ENSG00000143324',
}


class WriteVariantAnnotationsVCFTest(MockedReferenceDatasetsTestCase):
    @patch(
        'loading_pipeline.lib.tasks.write_new_variants_table.load_gencode_gene_symbol_to_gene_id',
    )
    def test_sv_export_vcf(
        self,
        mock_load_gencode: Mock,
    ) -> None:
        copy_project_pedigree_to_mocked_dir(
            TEST_PEDIGREE_5,
            ReferenceGenome.GRCh38,
            DatasetType.SV,
            SampleType.WGS,
            'R0115_test_project2',
        )
        mock_load_gencode.return_value = GENE_ID_MAPPING
        worker = luigi.worker.Worker()
        update_variant_annotations_task = (
            UpdateVariantAnnotationsTableWithNewVariantsTask(
                reference_genome=ReferenceGenome.GRCh38,
                dataset_type=DatasetType.SV,
                run_id='run_id1',
                sample_type=SampleType.WGS,
                callset_path=TEST_SV_VCF,
                project_guids=['R0115_test_project2'],
                validations_to_skip=[ALL_VALIDATIONS],
                skip_expect_tdr_metrics=True,
            )
        )
        worker.add(update_variant_annotations_task)
        worker.run()
        self.assertTrue(update_variant_annotations_task.complete())
        write_variant_annotations_vcf_task = WriteVariantAnnotationsVCF(
            reference_genome=ReferenceGenome.GRCh38,
            dataset_type=DatasetType.SV,
            run_id='run_id1',
            sample_type=SampleType.WGS,
            callset_path=TEST_SV_VCF,
        )
        worker.add(write_variant_annotations_vcf_task)
        worker.run()
        self.assertTrue(
            hfs.exists(
                write_variant_annotations_vcf_task.output().path,
            ),
        )
        with hfs.open(write_variant_annotations_vcf_task.output().path, 'rb') as f:
            buf = f.read()
            self.assertTrue(gzip.decompress(buf).startswith(b'##fileformat=VCFv4.2'))
