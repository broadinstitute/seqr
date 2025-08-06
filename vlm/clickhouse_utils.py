import clickhouse_connect
import hail as hl
import os

CLICKHOUSE_CONNECTION_PARAMS = {
    'host': os.environ.get('CLICKHOUSE_SERVICE_HOSTNAME'),
    'port': os.environ.get('CLICKHOUSE_SERVICE_PORT'),
    'username': os.environ.get('CLICKHOUSE_USERNAME'),
    'password': os.environ.get('CLICKHOUSE_PASSWORD'),
    'database': os.environ.get('CLICKHOUSE_DATABASE', 'seqr'),
}


def get_clickhouse_variant_counts(locus: hl.LocusExpression, ref: str, alt: str, genome_build: str) -> hl.Struct:
    locus = hl.eval(locus)
    client = clickhouse_connect.get_client(**CLICKHOUSE_CONNECTION_PARAMS)
    results = client.query(
         "SELECT plus(gt_stats.1, gt_stats.2), plus(gt_stats.3, gt_stats.4) FROM (SELECT dictGet(%(dict_name)s, ('ac_wes', 'ac_wgs', 'hom_wes', 'hom_wgs'), key) AS gt_stats FROM %(table_name)s WHERE variantId=%(variant_id)s)",
        parameters={
            'variant_id': f'{locus.contig.replace("chr", "")}-{locus.position}-{ref}-{alt}',
            'table_name': f'{genome_build}/SNV_INDEL/key_lookup',
            'dict_name': f'{genome_build}/SNV_INDEL/gt_stats_dict',
        },
    ).result_set
    return results[0] if results else (0, 0)
