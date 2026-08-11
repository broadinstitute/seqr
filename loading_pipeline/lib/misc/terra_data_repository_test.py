import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import responses

from loading_pipeline.lib.misc.terra_data_repository import (
    TDR_ROOT_URL,
    _get_dataset_ids,
    bq_metrics_query,
    gen_bq_table_names,
)

TDR_DATASETS = [
    {
        'id': '2dc51ee0-a037-499d-a915-a7c20a0b216d',
        'name': 'RP_3053',
        'description': 'TGG_Ware_DRAGEN_hg38. Dataset automatically created and linked to: RP-3053',
        'defaultProfileId': '0a164b9a-2b8b-45d2-859e-a4e369b9cb4f',
        'createdDate': '2023-10-05T13:15:27.649760Z',
        'storage': [
            {
                'region': 'us-central1',
                'cloudResource': 'bigquery',
                'cloudPlatform': 'gcp',
            },
            {
                'region': 'us-east4',
                'cloudResource': 'firestore',
                'cloudPlatform': 'gcp',
            },
            {
                'region': 'us-central1',
                'cloudResource': 'bucket',
                'cloudPlatform': 'gcp',
            },
        ],
        'secureMonitoringEnabled': False,
        'cloudPlatform': 'gcp',
        'dataProject': 'datarepo-7242affb',
        'storageAccount': None,
        'phsId': None,
        'selfHosted': False,
        'predictableFileIds': False,
        'tags': [],
        'resourceLocks': {
            'exclusive': None,
            'shared': [],
        },
    },
    {
        'id': 'beef77e8-575b-40e5-9340-a6f10e0bec67',
        'name': 'RP_3056',
        'description': 'RGP_HMB_DRAGEN_hg38. Dataset automatically created and linked to: RP-3056',
        'defaultProfileId': '835dd05d-c603-4b0d-926f-d9143fd24549',
        'createdDate': '2023-10-05T20:15:27.622481Z',
        'storage': [
            {
                'region': 'us-central1',
                'cloudResource': 'bigquery',
                'cloudPlatform': 'gcp',
            },
            {
                'region': 'us-east4',
                'cloudResource': 'firestore',
                'cloudPlatform': 'gcp',
            },
            {
                'region': 'us-central1',
                'cloudResource': 'bucket',
                'cloudPlatform': 'gcp',
            },
        ],
        'secureMonitoringEnabled': False,
        'cloudPlatform': 'gcp',
        'dataProject': 'datarepo-5a72e31b',
        'storageAccount': None,
        'phsId': None,
        'selfHosted': False,
        'predictableFileIds': False,
        'tags': [],
        'resourceLocks': {
            'exclusive': None,
            'shared': [],
        },
    },
    {
        'id': 'c8d74ac4-9a2e-4d3d-a6b5-1f4b433d949f',
        'name': 'RP_3055',
        'description': 'RGP_GRU_DRAGEN_hg38. Dataset automatically created and linked to: RP-3055',
        'defaultProfileId': '835dd05d-c603-4b0d-926f-d9143fd24549',
        'createdDate': '2023-10-05T20:15:28.255304Z',
        'storage': [
            {
                'region': 'us-central1',
                'cloudResource': 'bigquery',
                'cloudPlatform': 'gcp',
            },
            {
                'region': 'us-east4',
                'cloudResource': 'firestore',
                'cloudPlatform': 'gcp',
            },
            {
                'region': 'us-central1',
                'cloudResource': 'bucket',
                'cloudPlatform': 'gcp',
            },
        ],
        'secureMonitoringEnabled': False,
        'cloudPlatform': 'gcp',
        'dataProject': 'datarepo-0f5be351',
        'storageAccount': None,
        'phsId': None,
        'selfHosted': False,
        'predictableFileIds': False,
        'tags': [],
        'resourceLocks': {
            'exclusive': None,
            'shared': [
                'Gw_KTeYRS1aLhRvapMLYLg',
                'WrP-0w1aROOUbgkI8JS6Ug',
            ],
        },
    },
]


@patch(
    'loading_pipeline.lib.misc.terra_data_repository.get_service_account_credentials',
    return_value=SimpleNamespace(
        token='abcdefg',  # noqa: S106
    ),
)
class TerraDataRepositoryTest(unittest.TestCase):
    @responses.activate
    def test_get_dataset_ids(self, _: Mock) -> None:
        responses.get(
            os.path.join(TDR_ROOT_URL, 'datasets?limit=50000'),
            body=json.dumps(
                {
                    'total': 3,
                    'filteredTotal': 3,
                    'items': TDR_DATASETS,
                },
            ),
        )
        self.assertListEqual(
            _get_dataset_ids(),
            [
                '2dc51ee0-a037-499d-a915-a7c20a0b216d',
                'beef77e8-575b-40e5-9340-a6f10e0bec67',
                'c8d74ac4-9a2e-4d3d-a6b5-1f4b433d949f',
            ],
        )

    @responses.activate
    def test_get_dataset_ids_no_bq(self, _: Mock) -> None:
        responses.get(
            os.path.join(TDR_ROOT_URL, 'datasets'),
            body=json.dumps(
                {
                    'total': 1,
                    'filteredTotal': 1,
                    'items': [
                        {
                            'id': '2dc51ee0-a037-499d-a915-a7c20a0b216d',
                            'name': 'RP_3053',
                            'description': 'TGG_Ware_DRAGEN_hg38. Dataset automatically created and linked to: RP-3053',
                            'defaultProfileId': '0a164b9a-2b8b-45d2-859e-a4e369b9cb4f',
                            'createdDate': '2023-10-05T13:15:27.649760Z',
                            'storage': [
                                # NB: bigquery was removed from 'storage' here.
                                {
                                    'region': 'us-east4',
                                    'cloudResource': 'firestore',
                                    'cloudPlatform': 'gcp',
                                },
                                {
                                    'region': 'us-central1',
                                    'cloudResource': 'bucket',
                                    'cloudPlatform': 'gcp',
                                },
                            ],
                            'secureMonitoringEnabled': False,
                            'cloudPlatform': 'gcp',
                            'dataProject': 'datarepo-7242affb',
                            'storageAccount': None,
                            'phsId': None,
                            'selfHosted': False,
                            'predictableFileIds': False,
                            'tags': [],
                            'resourceLocks': {
                                'exclusive': None,
                                'shared': [],
                            },
                        },
                    ],
                },
            ),
        )
        self.assertRaises(
            ValueError,
            _get_dataset_ids,
        )

    @responses.activate
    def test_gen_bq_table_names(self, _: Mock) -> None:
        responses.get(
            os.path.join(TDR_ROOT_URL, 'datasets'),
            body=json.dumps(
                {
                    'total': 3,
                    'filteredTotal': 3,
                    'items': TDR_DATASETS,
                },
            ),
        )
        for dataset_id, name, project_name, dataset_name in [
            (
                '2dc51ee0-a037-499d-a915-a7c20a0b216d',
                'RP_3053',
                'datarepo-7242affb',
                'datarepo_RP_3053',
            ),
            (
                'beef77e8-575b-40e5-9340-a6f10e0bec67',
                'RP_3056',
                'datarepo-5a72e31b',
                'datarepo_RP_3056',
            ),
            (
                'c8d74ac4-9a2e-4d3d-a6b5-1f4b433d949f',
                'RP_3059',
                'datarepo-aada2e3b',
                'datarepo_RP_3059',
            ),
        ]:
            responses.get(
                os.path.join(
                    TDR_ROOT_URL,
                    f'datasets/{dataset_id}?include=ACCESS_INFORMATION',
                ),
                body=json.dumps(
                    {
                        'id': dataset_id,
                        'name': name,
                        'description': 'TGG_Ware_DRAGEN_hg38. Dataset automatically created and linked to: RP-3053',
                        'defaultProfileId': None,
                        'dataProject': None,
                        'defaultSnapshotId': None,
                        'schema': None,
                        'createdDate': '2023-10-05T13:15:27.649760Z',
                        'storage': None,
                        'secureMonitoringEnabled': False,
                        'phsId': None,
                        'accessInformation': {
                            'bigQuery': {
                                'datasetName': dataset_name,
                                'datasetId': f'{project_name}:{dataset_name}',
                                'projectId': project_name,
                                'link': 'https://console.cloud.google.com/bigquery?project=datarepo-7242affb&ws=!datarepo_RP_3053&d=datarepo_RP_3053&p=datarepo-7242affb&page=dataset',
                                'tables': [
                                    {
                                        'name': 'jointcallset',
                                        'id': f'{project_name}.{dataset_name}.jointcallset',
                                        'qualifiedName': 'datarepo-7242affb.datarepo_RP_3053.jointcallset',
                                        'link': 'https://console.cloud.google.com/bigquery?project=datarepo-7242affb&ws=!datarepo_RP_3053&d=datarepo_RP_3053&p=datarepo-7242affb&page=table&t=jointcallset',
                                        'sampleQuery': 'SELECT * FROM `datarepo-7242affb.datarepo_RP_3053.jointcallset`',
                                    },
                                    {
                                        'name': 'sample',
                                        'id': f'{project_name}.{dataset_name}.sample',
                                        'qualifiedName': 'datarepo-7242affb.datarepo_RP_3053.sample',
                                        'link': 'https://console.cloud.google.com/bigquery?project=datarepo-7242affb&ws=!datarepo_RP_3053&d=datarepo_RP_3053&p=datarepo-7242affb&page=table&t=sample',
                                        'sampleQuery': 'SELECT * FROM `datarepo-7242affb.datarepo_RP_3053.sample`',
                                    },
                                ],
                            },
                            'parquet': None,
                        },
                        'cloudPlatform': None,
                        'selfHosted': False,
                        'properties': None,
                        'ingestServiceAccount': None,
                        'predictableFileIds': False,
                        'tags': [],
                        'resourceLocks': {
                            'exclusive': None,
                            'shared': [],
                        },
                    },
                ),
            )
        self.assertCountEqual(
            list(gen_bq_table_names()),
            [
                'datarepo-7242affb.datarepo_RP_3053',
                'datarepo-5a72e31b.datarepo_RP_3056',
                'datarepo-aada2e3b.datarepo_RP_3059',
            ],
        )

    @patch('loading_pipeline.lib.misc.terra_data_repository.bigquery.Client')
    def test_bq_metrics_query_missing_metrics(
        self,
        mock_bq_client: Mock,
        _: Mock,
    ) -> None:
        mock_bq_client.return_value.query_and_wait.return_value = iter(
            [['predicted_sex,contamination_rate,percent_bases_at_20x']],
        )
        bq_metrics_query('datarepo-7242affb.datarepo_RP_3053')
        self.assertEqual(
            mock_bq_client.return_value.query_and_wait.mock_calls[1],
            call(
                '\n        SELECT predicted_sex,contamination_rate,percent_bases_at_20x,NULL AS collaborator_sample_id,NULL AS mean_coverage FROM `datarepo-7242affb.datarepo_RP_3053.sample`;\n        ',
            ),
        )
