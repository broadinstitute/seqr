from pathlib import Path

from aiohttp import web_exceptions
from aiohttp.test_utils import AioHTTPTestCase

from loading_pipeline.api.app import init_web_app
from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.test.mocked_dataroot_testcase import MockedDatarootTestCase

CALLSET_PATH = str(
    Path('loading_pipeline/var/test/callsets/1kg_30variants.vcf').resolve(),
)


class AppTest(AioHTTPTestCase, MockedDatarootTestCase):
    async def get_application(self):
        return await init_web_app()

    async def test_status(self):
        async with self.client.request('GET', '/status') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {'success': True})

    async def test_missing_route(self):
        with self.assertLogs(level='ERROR') as _:
            async with self.client.request('GET', '/loading_pip') as resp:
                self.assertEqual(resp.status, web_exceptions.HTTPNotFound.status_code)

    async def test_loading_pipeline_invalid_requests(self):
        with self.assertLogs(level='ERROR') as log:
            async with self.client.request('GET', '/loading_pipeline_enqueue') as resp:
                self.assertEqual(
                    resp.status,
                    web_exceptions.HTTPMethodNotAllowed.status_code,
                )
                self.assertTrue(
                    'HTTPMethodNotAllowed' in log.output[0],
                )

        with self.assertLogs(level='ERROR') as log:
            async with self.client.request('POST', '/loading_pipeline_enqueue') as resp:
                self.assertEqual(
                    resp.status,
                    web_exceptions.HTTPUnprocessableEntity.status_code,
                )
                self.assertTrue(
                    'HTTPUnprocessableEntity' in log.output[0],
                )

        body = {
            'callset_path': 'missing.vcf',
            'project_guids': ['project_a'],
            'sample_type': SampleType.WGS.value,
            'reference_genome': ReferenceGenome.GRCh38.value,
            'dataset_type': DatasetType.SNV_INDEL.value,
        }
        with self.assertLogs(level='ERROR') as log:
            async with self.client.request(
                'POST',
                '/loading_pipeline_enqueue',
                json=body,
            ) as resp:
                self.assertEqual(
                    resp.status,
                    web_exceptions.HTTPBadRequest.status_code,
                )
                self.assertTrue(
                    'callset_path must point to a file that exists' in log.output[0],
                )

        body = {
            'callset_path': CALLSET_PATH,
            'project_guids': ['project_a'],
            'sample_type': SampleType.WGS.value,
            'reference_genome': ReferenceGenome.GRCh38.value,
            'dataset_type': DatasetType.SNV_INDEL.value,
            'validations_to_skip': ['bad_validation'],
        }
        with self.assertLogs(level='ERROR') as log:
            async with self.client.request(
                'POST',
                '/loading_pipeline_enqueue',
                json=body,
            ) as resp:
                self.assertEqual(
                    resp.status,
                    web_exceptions.HTTPBadRequest.status_code,
                )
                self.assertTrue(
                    "input_value='bad_validation" in log.output[0],
                )

    async def test_loading_pipeline_enqueue(self):
        body = {
            'callset_path': CALLSET_PATH,
            'project_guids': ['project_a'],
            'sample_type': SampleType.WGS.value,
            'reference_genome': ReferenceGenome.GRCh38.value,
            'dataset_type': DatasetType.SNV_INDEL.value,
        }
        async with self.client.request(
            'POST',
            '/loading_pipeline_enqueue',
            json=body,
        ) as resp:
            self.assertEqual(
                resp.status,
                web_exceptions.HTTPAccepted.status_code,
            )
            resp_json = await resp.json()
        self.assertDictEqual(
            resp_json,
            {
                'Successfully queued': {
                    'request_type': 'LoadingPipelineRequest',
                    'callset_path': CALLSET_PATH,
                    'dataset_type': 'SNV_INDEL',
                    'project_guids': ['project_a'],
                    'reference_genome': 'GRCh38',
                    'sample_type': 'WGS',
                    'skip_check_sex_and_relatedness': False,
                    'skip_expect_tdr_metrics': False,
                    'attempt_id': 0,
                    'validations_to_skip': [],
                },
            },
        )

        # Second request
        body['project_guids'] = ['project_b', 'project_c']
        async with self.client.request(
            'POST',
            '/loading_pipeline_enqueue',
            json=body,
        ) as resp:
            self.assertEqual(
                resp.status,
                web_exceptions.HTTPAccepted.status_code,
            )
