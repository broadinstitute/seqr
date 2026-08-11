import unittest

from loading_pipeline.lib.core import Env
from loading_pipeline.lib.misc.clickhouse import (
    STAGING_CLICKHOUSE_DATABASE,
    get_clickhouse_client,
)

TEST_SCHEMA = 'loading_pipeline/var/test/test_clickhouse_schema.sql'


class ClickhouseSchemaTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        client = get_clickhouse_client()
        client.execute(
            f"""
            DROP DATABASE IF EXISTS {STAGING_CLICKHOUSE_DATABASE};
            """,
        )
        client.execute(
            f"""
            DROP DATABASE IF EXISTS {Env.CLICKHOUSE_DATABASE};
            """,
        )
        client.execute(
            f"""
            CREATE DATABASE {Env.CLICKHOUSE_DATABASE};
        """,
        )
        client = get_clickhouse_client(database=Env.CLICKHOUSE_DATABASE)
        client.execute(
            """
            CREATE DICTIONARY seqrdb_gene_ids
            (
                `gene_id` String,
                `seqrdb_id` String,
                `affected` String
            )
            PRIMARY KEY gene_id
            SOURCE(NULL())
            LIFETIME(0)
            LAYOUT(HASHED())
            """,
        )
        client.execute(
            """
            CREATE DICTIONARY seqrdb_affected_status_dict
            (
                `family_guid` String,
                `sampleId` String,
                `affected` String
            )
            PRIMARY KEY family_guid, sampleId
            SOURCE(NULL())
            LIFETIME(0)
            LAYOUT(COMPLEX_KEY_HASHED())
            """,
        )
        client.execute(
            """
            CREATE DICTIONARY `GRCh38/SNV_INDEL/project_partitions_dict`
            (
                `project_guid` String,
                `n_partitions` UInt32
            )
            PRIMARY KEY project_guid
            SOURCE(NULL())
            LIFETIME(0)
            LAYOUT(COMPLEX_KEY_HASHED())
            """,
        )
        client.execute(
            """
            CREATE DICTIONARY `GRCh38/SNV_INDEL/reference_data/gnomad_genomes`
            (
                `key` UInt32,
                `filter_af` Decimal(9, 8)
            )
            PRIMARY KEY key
            SOURCE(NULL())
            LIFETIME(0)
            LAYOUT(COMPLEX_KEY_HASHED())
            """,
        )
        with open(TEST_SCHEMA) as f:
            sql = f.read()
        commands = [cmd.strip() for cmd in sql.split(';') if cmd.strip()]
        for cmd in commands:
            client.execute(cmd)
        client.execute(
            f"""
            CREATE DICTIONARY `GRCh38/SNV_INDEL/gt_stats_dict`
            (
                `key` UInt32,
                `ac_wes` UInt64,
                `ac_wgs` UInt64,
                `ac_affected` UInt64,
                `hom_wes` UInt64,
                `hom_wgs` UInt64,
                `hom_affected` UInt64
            )
            PRIMARY KEY key
            SOURCE(
                CLICKHOUSE(
                    USER {Env.CLICKHOUSE_WRITER_USER} PASSWORD {Env.CLICKHOUSE_WRITER_PASSWORD}
                    DB {Env.CLICKHOUSE_DATABASE} TABLE `GRCh38/SNV_INDEL/gt_stats`
                )
            )
            LIFETIME(0)
            LAYOUT(FLAT(MAX_ARRAY_SIZE 1000000000))
            """,
        )

    def tearDown(self):
        super().tearDown()
        client = get_clickhouse_client()
        client.execute(
            f"""
           DROP DATABASE IF EXISTS {STAGING_CLICKHOUSE_DATABASE};
           """,
        )
        client.execute(
            f"""
           DROP DATABASE IF EXISTS {Env.CLICKHOUSE_DATABASE};
           """,
        )
