import os
import re
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

import google.cloud.bigquery
from google.cloud import bigquery

from loading_pipeline.lib.misc.gcp import get_service_account_credentials
from loading_pipeline.lib.misc.requests import requests_retry_session

BIGQUERY_METRICS = [
    'predicted_sex',
    'contamination_rate',
    'percent_bases_at_20x',
    'collaborator_sample_id',
    'mean_coverage',
]
BIGQUERY_RESOURCE = 'bigquery'
TABLE_NAME_VALIDATION_REGEX = r'datarepo-\w+.datarepo_\w+'
TDR_ROOT_URL = 'https://data.terra.bio/api/repository/v1/'


def _tdr_request(resource: str) -> dict:
    service_account_token = get_service_account_credentials().token
    s = requests_retry_session()
    res = s.get(
        url=os.path.join(TDR_ROOT_URL, resource),
        headers={'Authorization': f'Bearer {service_account_token}'},
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


def _get_dataset_ids() -> list[str]:
    res_body = _tdr_request('datasets?limit=50000')  # Arbitrary large number :/
    items = res_body['items']
    for item in items:
        if not any(x['cloudResource'] == BIGQUERY_RESOURCE for x in item['storage']):
            # Hard failure on purpose to prompt manual investigation.
            msg = 'Datasets without bigquery sources are unsupported'
            raise ValueError(msg)
    return [x['id'] for x in items]


def gen_bq_table_names() -> Generator[str]:
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(
                _tdr_request,
                f'datasets/{dataset_id}?include=ACCESS_INFORMATION',
            )
            for dataset_id in _get_dataset_ids()
        ]
        for future in as_completed(futures):
            result = future.result()
            yield f'{result["accessInformation"]["bigQuery"]["projectId"]}.{result["accessInformation"]["bigQuery"]["datasetName"]}'


def bq_metrics_query(bq_table_name: str) -> google.cloud.bigquery.table.RowIterator:
    if not re.match(TABLE_NAME_VALIDATION_REGEX, bq_table_name):
        msg = f'{bq_table_name} does not match expected pattern'
        raise ValueError(msg)
    client = bigquery.Client()

    # not all columns are guaranteed to be present, coalesce if missing
    table_ddl = next(
        client.query_and_wait(
            f"""
        SELECT ddl FROM `{bq_table_name}`.INFORMATION_SCHEMA.TABLES where table_name='sample';
        """,  # noqa: S608
        ),
    )[0]
    metrics = [(m if m in table_ddl else f'NULL AS {m}') for m in BIGQUERY_METRICS]
    return client.query_and_wait(
        f"""
        SELECT {','.join(metrics)} FROM `{bq_table_name}.sample`;
        """,  # noqa: S608
    )
