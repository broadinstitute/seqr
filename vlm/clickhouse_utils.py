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
        f"SELECT dictGet(`{genome_build}/SNV_INDEL/gt_stats_dict`, ('ac_wes', 'ac_wgs', 'hom_wes', 'hom_wgs'), key) FROM `{genome_build}/SNV_INDEL/key_lookup` WHERE variantId=%(variant_id)s",
        parameters={'variant_id': f'{locus.contig.replace("chr", "")}-{locus.position}-{ref}-{alt}'},
    ).result_set
    return (results[0]['ac_wes'] + results[0]['ac_wgs'], results[0]['hom_wes'] + results[0]['hom_wgs']) if results else (0, 0)

