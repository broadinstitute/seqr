####################################################
#
# This script is provided as means to repartition an existing `GRCh38/SNV_INDEL/entries` table
# from a project-only partitioning strategy to one that includes project subpartitions.
# Very large genome projects with thousands of families will require additional
# splitting to maintain reasonable loading performance and to keep partition size under
# the recommended ClickHouse maximum.  Unfortunately, a ClickHouse table partition definition
# is static upon creation, necessitating the expensive table re-write process demonstrated below.
#
# Post seqr-platform version x.x.x, the subpartition-ing strategy is provided by default;
# earlier installations will continue to function as-is.  This script is meant to
# be run under human supervision and with caution.
#
# At the end of this script, you should run the following SQL to finalize the migration:
# EXCHANGE TABLES seqr.'GRCh38/SNV_INDEL/entries' AND staging_grch38_snvindel_repartition.'GRCh38/SNV_INDEL/repartitioned_entries'
# DROP DATABASE `staging_grch38_snvindel_repartition`;
#
# Resource Requirements:
# - Free disk space equal to 2.5x the usage of your current `GRCh38/SNV_INDEL/entries` table.
#
####################################################
import argparse

from loading_pipeline.lib.core.environment import Env
from loading_pipeline.lib.misc.clickhouse import (
    logged_query,
    normalize_partition,
)

REPARTITION_DATABASE_NAME = 'staging_grch38_snvindel_repartition'


def get_partitions_for_project(project_guid: str):
    rows = logged_query(
        """
        SELECT DISTINCT partition
        FROM system.parts
        WHERE
            database = %(database)s
            AND table = %(table)s
            AND partition like %(project_guid)s
        """,
        {
            'database': REPARTITION_DATABASE_NAME,
            'table': 'GRCh38/SNV_INDEL/repartitioned_entries',
            'project_guid': f'%{project_guid}%',
        },
    )
    return [normalize_partition(row[0]) for row in rows]


def main(max_insert_threads: int, project_guids: list[str]):
    logged_query(
        f"""
        CREATE DATABASE IF NOT EXISTS {REPARTITION_DATABASE_NAME};
        """,
    )
    logged_query(
        f"""
        CREATE TABLE IF NOT EXISTS {REPARTITION_DATABASE_NAME}.`GRCh38/SNV_INDEL/repartitioned_entries`
        AS {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries`
        ENGINE = CollapsingMergeTree(sign)
        PARTITION BY (project_guid, partition_id)
        SETTINGS deduplicate_merge_projection_mode = 'rebuild'
        """,
    )
    if not project_guids:
        project_guids = [
            x[0]
            for x in logged_query(
                f"""
            SELECT DISTINCT project_guid from {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries`
            """,
            )
        ]
    for project_guid in project_guids:
        for partition in get_partitions_for_project(
            project_guid,
        ):
            logged_query(
                f"""
                ALTER TABLE {REPARTITION_DATABASE_NAME}.`GRCh38/SNV_INDEL/repartitioned_entries`
                DROP PARTITION %(partition)s
                """,
                {'partition': partition},
            )
        logged_query(
            f"""
            INSERT INTO {REPARTITION_DATABASE_NAME}.`GRCh38/SNV_INDEL/repartitioned_entries`
            SELECT * FROM {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries`
            WHERE project_guid=%(project_guid)s
            SETTINGS max_insert_threads=%(max_insert_threads)s
            """,
            {'project_guid': project_guid, 'max_insert_threads': max_insert_threads},
            timeout=99999,
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--max-insert-threads',
        type=int,
        default=4,
        help='Maximum number of insert threads to use (default: 4).',
    )
    parser.add_argument(
        '--project-guids',
        nargs='+',
        required=False,
        help='Optionally provide an override list of project guids: --project-guids proj1 proj2 proj3',
    )
    args = parser.parse_args()
    main(args.max_insert_threads, args.project_guids)
