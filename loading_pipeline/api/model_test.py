import unittest
from pathlib import Path

from loading_pipeline.api.model import DeleteFamiliesRequest, LoadingPipelineRequest
from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType

CALLSET_PATH = str(
    Path('loading_pipeline/var/test/callsets/1kg_30variants.vcf').resolve(),
)


class ModelTest(unittest.TestCase):
    def test_valid_loading_pipeline_requests(self) -> None:
        raw_request = {
            'callset_path': CALLSET_PATH,
            'projects_to_run': ['project_a'],
            'sample_type': SampleType.WGS.value,
            'reference_genome': ReferenceGenome.GRCh38.value,
            'dataset_type': DatasetType.SNV_INDEL.value,
        }
        lpr = LoadingPipelineRequest.model_validate(raw_request)
        self.assertEqual(lpr.reference_genome, ReferenceGenome.GRCh38)
        self.assertEqual(lpr.project_guids, ['project_a'])
        self.assertEqual(lpr.request_type, 'LoadingPipelineRequest')
        self.assertEqual(lpr.attempt_id, 0)

        # Test wildcard VCF
        raw_request['callset_path'] = CALLSET_PATH.replace(
            '1kg_30variants.vcf',
            '1kg_30*.vcf',
        )
        lpr = LoadingPipelineRequest.model_validate(raw_request)

    def test_invalid_loading_pipeline_requests(self) -> None:
        raw_request = {
            'callset_path': 'a.txt',
            'project_guids': [],
            'sample_type': 'BLENDED',
            'reference_genome': ReferenceGenome.GRCh38.value,
            'dataset_type': DatasetType.SNV_INDEL.value,
            'attempt_id': 5,
        }
        with self.assertRaises(ValueError) as cm:
            LoadingPipelineRequest.model_validate(raw_request)
        self.assertTrue(
            str(cm.exception).startswith(
                '4 validation errors for LoadingPipelineRequest',
            ),
        )

    def test_validations_to_skip(self) -> None:
        shared_params = {
            'callset_path': CALLSET_PATH,
            'projects_to_run': ['project_a'],
            'sample_type': SampleType.WGS.value,
            'reference_genome': ReferenceGenome.GRCh38.value,
            'dataset_type': DatasetType.SNV_INDEL.value,
        }
        raw_request = {
            **shared_params,
            'validations_to_skip': ['all'],
        }
        lpr = LoadingPipelineRequest.model_validate(raw_request)
        self.assertGreater(len(lpr.validations_to_skip), 2)

        raw_request = {
            **shared_params,
            'validations_to_skip': ['validate_sample_type'],
        }
        lpr = LoadingPipelineRequest.model_validate(raw_request)
        self.assertEqual(len(lpr.validations_to_skip), 1)

        raw_request = {
            **shared_params,
            'validations_to_skip': ['validate_blended_exome'],
        }
        with self.assertRaises(ValueError):
            LoadingPipelineRequest.model_validate(raw_request)

    def test_delete_families_request(self) -> None:
        raw_request = {'project_guid': 'project_a', 'family_guids': []}
        with self.assertRaises(ValueError):
            DeleteFamiliesRequest.model_validate(raw_request)
        raw_request['family_guids'] = ['family_a1']
        dfr = DeleteFamiliesRequest.model_validate(raw_request)
        self.assertEqual(dfr.project_guid, 'project_a')
        self.assertEqual(dfr.request_type, 'DeleteFamiliesRequest')
