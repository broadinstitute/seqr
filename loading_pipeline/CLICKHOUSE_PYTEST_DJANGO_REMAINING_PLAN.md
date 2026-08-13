# Plan: Finish migrating `repartition_clickhouse_grch38_snv_indel_test.py` to pytest-django

## Context

`loading_pipeline`'s ClickHouse tests were migrated to run against real `clickhouse_search`
Django migrations via pytest-django, with a shared `ClickhouseSchemaTestCase` base
(`lib/test/clickhouse_schema_testcase.py`) that owns the real schema DB's migrate/truncate
lifecycle. Every ClickHouse-touching test file adopted this base and switched from raw
`clickhouse_driver.Client` (`get_clickhouse_client()`) to
`connections['clickhouse_write'].cursor()` — except one file.

## Remaining work

`ops/repartition_clickhouse_grch38_snv_indel_test.py` (`RepartitionGRCh38SnvIndelTest`) still
predates the migration:

- extends bare `unittest.TestCase`, not `ClickhouseSchemaTestCase`
- `setUp` manually runs `DROP DATABASE IF EXISTS {Env.CLICKHOUSE_DATABASE} PARALLEL WITH DROP
  DATABASE IF EXISTS {REPARTITION_DATABASE_NAME}` then the matching `CREATE DATABASE ... PARALLEL
  WITH ...` — `Env.CLICKHOUSE_DATABASE` is now owned by pytest-django's migrate lifecycle;
  `REPARTITION_DATABASE_NAME` is the script's own scratch DB, not part of `clickhouse_search`'s
  schema
- every SQL statement in `setUp` and both test methods runs via `get_clickhouse_client()` +
  `client.execute(...)`, a raw `clickhouse_driver.Client`

### Changes

1. `RepartitionGRCh38SnvIndelTest` extends `ClickhouseSchemaTestCase` instead of
   `unittest.TestCase`.
2. Drop the `DROP DATABASE IF EXISTS {Env.CLICKHOUSE_DATABASE}` / `CREATE DATABASE
   {Env.CLICKHOUSE_DATABASE}` half of `setUp`'s `PARALLEL WITH` statements — the shared base now
   handles that DB's schema/lifecycle.
3. Keep the `REPARTITION_DATABASE_NAME` drop/create in `setUp` (still not part of the real
   schema), issued as its own statement.
4. Keep the synthetic `GRCh38/SNV_INDEL/entries` table DDL, `INSERT` seed rows, and
   `project_partitions_dict` dictionary DDL as-is (intentionally bespoke, not real schema).
5. Execute everything in `setUp` and both test methods (`test_main_all_projects`,
   `test_main_one_project`) via `connections['clickhouse_write'].cursor()` /
   `cursor.execute(...)` / `cursor.fetchall()` instead of `get_clickhouse_client()` /
   `client.execute(...)`.
6. Drop the now-unused `get_clickhouse_client` import.

Reference `lib/misc/clickhouse_test.py` or `bin/pipeline_worker_test.py` for the established
pattern of extending `ClickhouseSchemaTestCase` and using the cursor.