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

CHROMOSOMES = [
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19',
    '20', '21', '22', 'X', 'Y', 'M',
]


def get_clickhouse_variant_counts(chrom: str, pos: int, genome_build: str, ref: str, alt: str) -> Optional[Tuple[int, int]]:
    query = "SELECT plus(gt_stats.1, gt_stats.2), plus(gt_stats.3, gt_stats.4) FROM (SELECT dictGet(%(gt_stats_dict)s, ('ac_wes', 'ac_wgs', 'hom_wes', 'hom_wgs'), key) AS gt_stats FROM %(key_lookup_table)s WHERE variantId=%(variant_id)s)"
    params = {'gt_stats_dict': f'{genome_build}/SNV_INDEL/gt_stats_dict'}
    results = _get_clickhouse_variant_query_result(chrom, pos, genome_build, ref, alt, query, params)
    return results[0] if results else None


def get_clickhouse_variant_details(chrom: str, pos: int, genome_build: str, ref: str, alt: str) -> list[tuple]:
    query = """SELECT arrayMap(
      x -> tupleConcat((
        dictGetOrDefault(seqrdb_affected_status_dict, 'affected', (family_guid, x.sampleId), 'U'), 
        dictGetOrDefault(seqrdb_sex_dict, 'sex', (family_guid, x.sampleId), 'U')), 
        x.gt, 
        dictGet(seqrdb_individual_metadata_dict, ('restrict_sharing', 'features', 'omim_id', 'mondo_id', 'is_solved', 'vlm_contact_email'), (family_guid, x.sampleId))
    ), arrayFilter(c -> c.gt > 0, calls)), 
    has(discovery_families, family_guid), 
    has(excluded_families, family_guid) 
    FROM (
        SELECT key, 
        dictGet(seqrdb_discovery_variant_dict, 'family_guids', (key, 'SNV_INDEL')) AS discovery_families, 
        dictGet(seqrdb_excluded_variant_dict, 'family_guids', (key, 'SNV_INDEL')) AS excluded_families 
        FROM %(key_lookup_table)s WHERE variantId=%(variant_id)s
    ) AS lookup INNER JOIN %(entries_table)s entries ON entries.key = lookup.key WHERE xpos=%(xpos)s ORDER BY entries.family_guid"""
    params = {
        'entries_table': f'{genome_build}/SNV_INDEL/entries',
        'xpos': ((1 + CHROMOSOMES.index(chrom))*int(1e9)) + pos,
    }
    return _get_clickhouse_variant_query_result(chrom, pos, genome_build, ref, alt, query, params)


def _get_clickhouse_variant_query_result(chrom: str, pos: int, genome_build: str, ref: str, alt: str, query: str, params: dict) -> list[tuple]:
    client = clickhouse_connect.get_client(**CLICKHOUSE_CONNECTION_PARAMS)
    return client.query(
        query,
        parameters={
            'variant_id': f'{chrom}-{pos}-{ref}-{alt}',
            'key_lookup_table': f'{genome_build}/SNV_INDEL/key_lookup',
            **params,
        },
    ).result_set
