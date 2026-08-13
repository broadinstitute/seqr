# Plan: Manage ClickHouse test DB via pytest-django + `clickhouse_search` migrations

## Goal

Stop hand-maintaining ClickHouse schema DDL (and the static `var/test/test_clickhouse_schema.sql`
dump) inside `loading_pipeline`'s tests. Instead, use `pytest-django` to create/migrate the
ClickHouse test database from the real Django migrations in `clickhouse_search` (the source of
truth for the schema), so the pipeline's tests can never drift from production schema.

Scope constraint: all code changes live in `loading_pipeline/` or in
`.github/workflows/pipeline-unit-tests.yml`. Nothing in `clickhouse_search/` or root `settings.py`
is modified.

## Key constraint discovered

`clickhouse_search/backend/base.py` does a **bare** `from settings import
CLICKHOUSE_WRITER_USER, CLICKHOUSE_WRITER_PASSWORD, DATABASES` — not `django.conf.settings`. This
only resolves correctly if a top-level module literally named `settings` is importable on
`sys.path`. Today that resolves to the main repo's heavy `settings.py` (postgres, guardian,
social_django, google.auth, etc.) whenever cwd is the repo root — which is undesirable/impossible
to depend on from `loading_pipeline`'s minimal env.

**Trick:** create our own minimal module named `settings.py`, placed in a directory that we add to
`sys.path` ahead of the repo root (via pytest's `pythonpath` ini option, which prepends to
`sys.path`). That module serves double duty:
- It's what `clickhouse_search/backend/base.py`'s bare `import settings` resolves to.
- It's also `DJANGO_SETTINGS_MODULE` for pytest-django.

## Single connection / single set of credentials only

Per explicit direction: the settings module must configure **one** ClickHouse connection with
**one** set of credentials — not the production split of a read-only `clickhouse` alias plus a
privileged `clickhouse_write` alias. `DATABASES` will define a single real alias using one
writer-capable credential (needed anyway, since migrations and test data inserts require write
access).

That real alias must be named `clickhouse_write`, not `clickhouse`: `ClickHouseRouter.allow_migrate`
(`clickhouse_search/models/__init__.py`) hardcodes `db == 'clickhouse_write'` for the
`clickhouse_search` app, so only an alias literally named `clickhouse_write` is allowed to have
migrations applied to it.

Nuance to account for: `clickhouse_search/backend/base.py`'s `_dictionary_sql` looks up
`DATABASES['clickhouse_write']['NAME']` (for ClickHouse-sourced dictionaries with a
`clickhouse_query_template`) and `DATABASES[postgres_db]['NAME']` (default alias `'default'`, for
Postgres-sourced dictionaries) purely to embed a database *name string* into generated DDL — not to
open a second real connection. To keep this working without standing up a second live connection:
- Give `'clickhouse'` a `TEST: {'MIRROR': 'clickhouse_write'}` config, so Django reuses the
  `clickhouse_write` alias's actual test database instead of creating/tearing down a second one,
  while the key is still present for the `NAME` lookup (used only by `backend/base.py`, not by our
  own test code).
- Give `'default'` a placeholder entry (e.g. `ENGINE: 'django.db.backends.dummy'`) purely so
  `DATABASES['default']['NAME']` resolves to a string — nothing in `loading_pipeline`'s tests
  actually connects to it, since there's no Postgres in this CI job.

Test code (and the shared base class) uses `connections['clickhouse_write']` — the one alias
Django actually creates/migrates a real test database for.

## Inventory of every ClickHouse-touching test

1. **`lib/misc/clickhouse_test.py`** (`ClickhouseTest`) — hand-rolls ~250 lines of `CREATE
   TABLE`/`CREATE DICTIONARY`/`CREATE MATERIALIZED VIEW` DDL duplicating a subset of the real
   schema, plus fixture dictionaries for gene IDs/gnomAD.
2. **`lib/test/clickhouse_schema_testcase.py`** (`ClickhouseSchemaTestCase`) — loads the static
   `var/test/test_clickhouse_schema.sql` dump plus a few placeholder dictionaries. Used by:
   - `bin/pipeline_worker_test.py` (`PipelineWorkerTest`)
   - `lib/tasks/variants_migration/load_clickhouse_variants_tables_test.py`
     (`LoadClickhouseVariantsTablesTaskTest`)
3. **`ops/repartition_clickhouse_grch38_snv_indel_test.py`** (`RepartitionGRCh38SnvIndelTest`) —
   its own bespoke DDL for a synthetic, intentionally-simplified `entries` table + a wholly
   separate scratch database (`REPARTITION_DATABASE_NAME`) that isn't part of `clickhouse_search`'s
   schema at all.

## The Postgres/GCS-sourced dictionary wrinkle

A handful of dictionaries are, in production, sourced from Postgres (via the
`seqr_postgres_named_collection` named collection) or from GCS parquet URLs:

- `seqrdb_gene_ids`
- `seqrdb_affected_status_dict`
- `GRCh38/SNV_INDEL/project_partitions_dict`
- the gnomAD reference dict (`GRCh38/SNV_INDEL/reference_data/gnomad_genomes`)

`loading_pipeline`'s CI only runs ClickHouse (no Postgres, no GCS access). Running
`clickhouse_search`'s real migrations here requires a dummy `seqr_postgres_named_collection` (a new
workflow step, mirroring what `unit-tests.yml` already does for the main app) just so the
`CREATE DICTIONARY ... SOURCE(POSTGRESQL(NAME 'seqr_postgres_named_collection' ...))` DDL parses.
Dictionaries are lazily loaded (`LIFETIME(0)`), so DDL creation succeeds even though the source is
unreachable — but tests still need to override these specific dictionaries with deterministic
fixture sources afterward (same idea as today's code, just trimmed to only this handful instead of
faking the whole schema).

## Raw SQL execution in tests: use the Django connection, not `clickhouse_driver.Client`

Every test currently calls `get_clickhouse_client()` (a raw `clickhouse_driver.Client`, see
`lib/misc/clickhouse.py`) to run setup/assertion SQL directly. Once the schema is Django-managed,
tests should execute their raw SQL through Django's own DB connection instead of a separate
`clickhouse_driver.Client` instance — i.e. `django.db.connections['clickhouse_write'].cursor()`
(the one real alias defined per "Single connection / single set of credentials only" above),
calling `cursor.execute(sql, params)` / `cursor.fetchall()`.

This is purely a *client* swap for test code — tests keep writing raw SQL strings (no ORM/model
queries), just executed via the Django connection so the tests exercise the same connection
machinery/test-DB aliasing that pytest-django set up, rather than opening an independent
`clickhouse_driver` connection that doesn't know about Django's test DB name remapping. Production
code in `lib/misc/clickhouse.py` (`get_clickhouse_client` and friends) is unaffected — this only
applies to test files themselves.

## Shared setup-time data: Django fixtures, not bulk INSERT statements

Some test data is inserted once in a test class's `setUp`/`setUpClass` and reused across multiple
test methods (e.g. the `seqrdb_gene_ids`/`gnomad_genomes` source-table rows in
`ClickhouseTest`/`ClickhouseSchemaTestCase`). That category of data should be loaded via Django's
fixture mechanism (JSON fixture files under a `fixtures/` dir, loaded with
`fixtures = [...]` on the `TestCase` subclass, or an explicit `call_command('loaddata', ...)`) —
not hand-written `INSERT INTO ... VALUES (...)` statements repeated/executed in `setUp`.

This only applies to shared, setup-time reference data with a real backing model in
`clickhouse_search` (e.g. the source tables behind `seqrdb_gene_ids`/`gnomad_genomes`). Since
`loaddata` populates rows through the model layer, the dictionary itself still needs an explicit
`RELOAD DICTIONARY`/refresh afterward (dictionaries aren't themselves loaddata targets — their
backing source table is). Data that's specific to a single test method's body/assertions (not
shared across tests) stays as raw SQL executed via the Django connection cursor, per the prior
note — this fixture rule is specifically about *repeated* setup-time data.

## Proposed change set

| File | Change |
|---|---|
| `clickhouse_search/models/search_models.py`, `clickhouse_search/backend/table_models.py`, `clickhouse_search/migrations/0040_gnomadnoncodingconstraintdict.py` | move `Projection` from `search_models.py` to `backend/table_models.py`; update the migration's import accordingly (✅ done) |
| `clickhouse_search/constants.py` | duplicate 4 constants out of `seqr.models.Individual` instead of importing it (✅ done) |
| `.github/workflows/pipeline-unit-tests.yml` | keep `CLICKHOUSE_DATABASE=test`; no named-collection step needed anymore (no Postgres-sourced dictionaries are reachable via the minimal settings module in the first place - see note below) |
| `loading_pipeline/pyproject.toml` | add `django`, `django-clickhouse-backend`, `pytest-django` dev deps; add `[tool.pytest.ini_options]` (`DJANGO_SETTINGS_MODULE`, `pythonpath`) |
| **new** `loading_pipeline/lib/test/clickhouse_django/settings.py` | minimal Django settings: one real `clickhouse` alias (single credential set), `clickhouse_write` mirrored onto it via `TEST: {MIRROR: 'clickhouse'}`, a dummy `default` placeholder (NAME only, no real connection), `clickhouse_backend` + `clickhouse_search` apps, `ClickHouseRouter`; doubles as the shadow `settings` module `clickhouse_search/backend/base.py` bare-imports |
| `lib/test/clickhouse_schema_testcase.py` | rewritten as the one shared base class: drop all manual DDL/SQL-file loading (schema now comes from real migrations via pytest-django), keep only the small external-sourced-dictionary overrides + per-test flush/truncate + staging-DB drop/create — all executed via `connections['clickhouse_write'].cursor()`; shared reference rows (e.g. gene-id/gnomAD source-table rows) loaded via Django `fixtures = [...]` instead of `INSERT` statements |
| **delete** `loading_pipeline/var/test/test_clickhouse_schema.sql` | no longer needed |
| **new** `loading_pipeline/lib/test/fixtures/*.json` | Django fixtures for the shared setup-time reference rows referenced above |
| `lib/misc/clickhouse_test.py` | `ClickhouseTest` extends the shared base instead of hand-building its own schema; keeps only its fixture-data seeding (via the new Django fixtures, not bulk `INSERT`) and parquet-writing setup; all `get_clickhouse_client()` calls in the test body replaced with the Django connection cursor |
| `bin/pipeline_worker_test.py`, `lib/tasks/variants_migration/load_clickhouse_variants_tables_test.py` | no structural change (already extend the shared base) — swap their `get_clickhouse_client()` assertion calls to the Django connection cursor; cleanup of now-dead references (e.g. leftover `TEST_SCHEMA` constant) |
| `ops/repartition_clickhouse_grch38_snv_indel_test.py` | switch to the shared base for the real-schema DB lifecycle; keep its own synthetic `entries`-table `REPLACE`/dict + `REPARTITION_DATABASE_NAME` handling since that's not part of `clickhouse_search`'s schema; swap `get_clickhouse_client()` for the Django connection cursor |

## Open risk / caveat

No live ClickHouse instance is available in the sandbox used to write this plan, so some runtime
specifics can't be verified ahead of time:
- Whether `TRUNCATE` behaves as expected on materialized views (regular vs. refreshable).
- Exact Django test-DB naming interplay with `Env.CLICKHOUSE_DATABASE` (need a `TEST: {NAME: ...}`
  override to avoid Django's default `test_` prefix mismatch).
- Whether `CREATE DICTIONARY ... SOURCE(POSTGRESQL(...))` DDL actually succeeds against a
  ClickHouse server with only a dummy/unreachable named collection registered.
- Whether raw SQL params/tuple-list inserts (e.g. `INSERT INTO ... VALUES` with a Python list of
  tuples, as `clickhouse_driver.Client.execute` supports today) work identically through
  `cursor.execute()`/`cursor.executemany()` on the Django ClickHouse backend, or need reshaping.

These should be shaken out against a real CI run / local ClickHouse instance once implemented.

## Deviations from this plan, found during implementation

Verified against a live ClickHouse instance. Recorded here for reference; this plan document
itself is not otherwise updated to match implementation.

**`clickhouse_search/` changes beyond the two already noted above** (both cleared with the user
before making them):
- Moved `conditionally_refresh_reference_dataset` from `models/reference_data_models.py` to
  `backend/table_models.py`, so migration 0040 doesn't need to import the live model modules (and
  therefore `seqr.models.Dataset`/`seqr.utils.xpos_utils.CHROMOSOME_CHOICES`) just to reach one
  helper function.
- Added `conditionally_reload_dictionary` (`backend/table_models.py`) and edited migrations 0043
  and 0044 to use it instead of hardcoded `RunSQL('SYSTEM RELOAD DICTIONARY ...')` - those forced
  a real synchronous Postgres connection during `migrate`, which no environment here has. This
  edits already-applied migration files, normally treated as an immutable historical record.

**A production dependency change:** `clickhouse-driver` bumped `0.2.9` -> `0.2.10` in
`loading_pipeline/pyproject.toml` (forced by `django-clickhouse-backend==1.6`'s own pin; matches
the main app's version). Not test-only.

**Bugs/gaps in this plan's own design, fixed - all confined to `loading_pipeline/`:**
- `reference_data` needs its own dummy `DATABASES` alias; the plan only accounted for `default`
  (`GeneIdDict`/`OmimDict` declare `postgres_db = 'reference_data'`).
- `DATABASES['clickhouse_write']['TEST']['DEPENDENCIES']` must be `[]`, or Django raises
  "Circular dependency in TEST[DEPENDENCIES]" (it assumes every alias depends on `default`).
- The `pythonpath` ordering described in this plan's original settings-module writeup was
  backwards; pytest builds `sys.path` in the *same* order as the `pythonpath` list, not reversed.
- `django_find_project = false` is required - pytest-django's `manage.py` auto-discovery
  otherwise force-inserts the repo root at `sys.path[0]`, re-shadowing `settings`.
- `CLICKHOUSE_IN_MEMORY_DIR`/`CLICKHOUSE_DATA_DIR` must default to different paths, or two
  `EmbeddedRocksDB` tables collide on the same file lock.
- A stub `seqr` package (`lib/test/clickhouse_django/seqr/`) is needed - not anticipated anywhere
  in this plan - because `clickhouse_search/backend/table_models.py` imports `SeqrLogger`, and
  migration 0040 has a named dependency on a specific `seqr` migration.
- The "no named-collection CI step needed" conclusion in this plan's own change-set table is
  right, but the "Postgres/GCS-sourced dictionary wrinkle" section above is stale/wrong about why
  - see the migration 0043/0044 edit above for the actual mechanism.

**Explicit user-directed deviations from this plan's design:**
- The shared base class does NOT keep "staging-DB drop/create" logic, contrary to this plan's
  change-set table - `loading_pipeline`'s own production code already drops/creates the staging
  DB defensively, so tests don't need to.
- Per-test cleanup in the shared base class is a `_fixture_teardown` override that truncates all
  live, non-`Dictionary`/`MaterializedView` tables directly via SQL - not Django's `flush` command,
  which relies on `apps.get_models()` and finds nothing (no `clickhouse_search` model modules are
  imported anywhere in `loading_pipeline`).

**Unresolved tension, not yet acted on:** this plan calls for shared reference data (e.g.
`seqrdb_gene_ids` source rows) to be loaded via Django fixtures (`loaddata`), which requires
importing the real model classes being loaded - but the user has since directed that fully
importing `clickhouse_search`'s live model modules is unacceptable for these tests. Needs
resolution before the fixture-loading step is implemented.