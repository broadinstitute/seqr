import clickhouse_connect
import os
from typing import Optional, Tuple


CLICKHOUSE_CONNECTION_PARAMS = {
    'host': os.environ.get('CLICKHOUSE_SERVICE_HOSTNAME'),
    'port': os.environ.get('CLICKHOUSE_SERVICE_PORT'),
    'username': os.environ.get('CLICKHOUSE_VLM_USERNAME'),
    'password': os.environ.get('CLICKHOUSE_VLM_PASSWORD'),
    'database': os.environ.get('CLICKHOUSE_DATABASE', 'seqr'),
}


def get_clickhouse_variant_counts(chrom: str, pos: int, genome_build: str, ref: str, alt: str) -> Optional[Tuple[int, int]]:
    query = "SELECT plus(gt_stats.1, gt_stats.2), plus(gt_stats.3, gt_stats.4) FROM (SELECT dictGet(%(dict_name)s, ('ac_wes', 'ac_wgs', 'hom_wes', 'hom_wgs'), key) AS gt_stats"
    params = {'dict_name': f'{genome_build}/SNV_INDEL/gt_stats_dict'}
    results = _get_clickhouse_variant_query_result(chrom, pos, genome_build, ref, alt, query, params)
    return results[0] if results else None


def get_clickhouse_variant_details(chrom: str, pos: int, genome_build: str, ref: str, alt: str) -> list[tuple]:
    # TODO real query
    query = "SELECT plus(gt_stats.1, gt_stats.2), plus(gt_stats.3, gt_stats.4) FROM (SELECT dictGet(%(dict_name)s, ('ac_wes', 'ac_wgs', 'hom_wes', 'hom_wgs'), key) AS gt_stats"
    params = {'dict_name': f'{genome_build}/SNV_INDEL/gt_stats_dict'}
    return _get_clickhouse_variant_query_result(chrom, pos, genome_build, ref, alt, query, params)


def _get_clickhouse_variant_query_result(chrom: str, pos: int, genome_build: str, ref: str, alt: str, query: str, params: dict) -> list[tuple]:
    client = clickhouse_connect.get_client(**CLICKHOUSE_CONNECTION_PARAMS)
    return client.query(
        query + ' FROM %(table_name)s WHERE variantId=%(variant_id)s)',
        parameters={
            'variant_id': f'{chrom}-{pos}-{ref}-{alt}',
            'table_name': f'{genome_build}/SNV_INDEL/key_lookup',
            **params,
        },
    ).result_set
