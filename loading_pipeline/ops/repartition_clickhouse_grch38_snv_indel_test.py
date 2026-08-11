import unittest

from loading_pipeline.lib.core.environment import Env
from loading_pipeline.lib.misc.clickhouse import get_clickhouse_client
from loading_pipeline.ops.repartition_clickhouse_grch38_snv_indel import (
    REPARTITION_DATABASE_NAME,
    main,
)


class RepartitionGRCh38SnvIndelTest(unittest.TestCase):
    def setUp(self):
        client = get_clickhouse_client()
        client.execute(
            f"""
            DROP DATABASE IF EXISTS {Env.CLICKHOUSE_DATABASE}
            PARALLEL WITH
            DROP DATABASE IF EXISTS {REPARTITION_DATABASE_NAME};
            """,
        )
        client.execute(
            f"""
            CREATE DATABASE {Env.CLICKHOUSE_DATABASE}
            PARALLEL WITH
            CREATE DATABASE {REPARTITION_DATABASE_NAME};
        """,
        )
        client.execute(
            f"""
            CREATE TABLE {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries` (
                `key` UInt32,
                `project_guid` LowCardinality(String),
                `family_guid` String,
                `is_annotated_in_any_gene` Boolean,
                `sign` Int8,
                `n_partitions` UInt8 MATERIALIZED 2,
                `partition_id` UInt8 MATERIALIZED farmHash64(family_guid) % n_partitions,
                PROJECTION xpos_projection
                (
                    SELECT *
                    ORDER BY is_annotated_in_any_gene
                )
            )
            ENGINE = CollapsingMergeTree(sign)
            PARTITION BY project_guid
            ORDER BY (project_guid, family_guid, key)
            SETTINGS deduplicate_merge_projection_mode = 'rebuild';
            """,
        )
        client.execute(
            f"""
            INSERT INTO {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/entries`
            VALUES
            (0, 'project_a', 'family_a1', 0,  1),
            (1, 'project_a', 'family_a2', 0,  1),
            (2, 'project_a', 'family_a3', 0,  1),
            (0, 'project_b', 'family_b1', 0,  1),
            (1, 'project_b', 'family_b2', 0,  1),
            (2, 'project_b', 'family_b2', 0,  1),
            (0, 'project_c', 'family_c1', 1,  1),
            (3, 'project_c', 'family_c2', 1,  1),
            """,
        )
        client.execute(
            f"""
            CREATE DICTIONARY {Env.CLICKHOUSE_DATABASE}.`GRCh38/SNV_INDEL/project_partitions_dict`
            (
                `project_guid` String,
                `n_partitions` UInt8
            )
            PRIMARY KEY project_guid
            SOURCE(
                CLICKHOUSE(
                    USER '{Env.CLICKHOUSE_WRITER_USER}' PASSWORD '{Env.CLICKHOUSE_WRITER_PASSWORD}'
                    DB {Env.CLICKHOUSE_DATABASE} QUERY 'SELECT project_guid, 3 FROM `GRCh38/SNV_INDEL/entries`'
                )
            )
            LIFETIME(0)
            LAYOUT(FLAT(MAX_ARRAY_SIZE 10000))
            """,
        )

    def test_main_all_projects(self):
        client = get_clickhouse_client()
        main(1, [])
        res = client.execute(
            f"""
            SELECT *, n_partitions, partition_id FROM {REPARTITION_DATABASE_NAME}.`GRCh38/SNV_INDEL/repartitioned_entries`
            """,
        )
        self.assertCountEqual(
            res,
            [
                (3, 'project_c', 'family_c2', True, 1, 2, 1),
                (0, 'project_b', 'family_b1', 0, 1, 2, 1),
                (1, 'project_b', 'family_b2', 0, 1, 2, 1),
                (2, 'project_b', 'family_b2', 0, 1, 2, 1),
                (2, 'project_a', 'family_a3', 0, 1, 2, 0),
                (0, 'project_a', 'family_a1', 0, 1, 2, 1),
                (1, 'project_a', 'family_a2', 0, 1, 2, 1),
                (0, 'project_c', 'family_c1', True, 1, 2, 0),
            ],
        )

    def test_main_one_project(self):
        client = get_clickhouse_client()
        main(1, ['project_a'])
        res = client.execute(
            f"""
            SELECT *, n_partitions, partition_id FROM {REPARTITION_DATABASE_NAME}.`GRCh38/SNV_INDEL/repartitioned_entries`
            """,
        )
        self.assertCountEqual(
            res,
            [
                (2, 'project_a', 'family_a3', 0, 1, 2, 0),
                (0, 'project_a', 'family_a1', 0, 1, 2, 1),
                (1, 'project_a', 'family_a2', 0, 1, 2, 1),
            ],
        )
