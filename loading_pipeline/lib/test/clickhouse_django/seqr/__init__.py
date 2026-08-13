"""Minimal stub of the main app's `seqr` package, for `loading_pipeline`'s tests only.

`clickhouse_search` (the source of truth for the ClickHouse schema, migrated via real Django
migrations in these tests - see `lib/test/clickhouse_django/settings.py`) has a small number of
genuine, unavoidable dependencies on the `seqr` app:
  - `clickhouse_search/backend/table_models.py` (needed to load `clickhouse_search`'s migrations)
    imports `seqr.utils.logging_utils.SeqrLogger` - a tiny, dependency-free logging wrapper.
  - `clickhouse_search`'s migration `0040_gnomadnoncodingconstraintdict.py` declares a
    cross-app migration dependency on a specific `seqr` migration (used only for historical
    migration-ordering purposes, not because it touches any `seqr` table).

Neither of these needs the *real* `seqr` app - which imports `django-guardian`,
`django.contrib.postgres`, `social_django`, etc. at module level via `seqr/models.py` - all
dependencies `loading_pipeline`'s minimal test environment intentionally does not install.

This package is placed in `lib/test/clickhouse_django/`, which pytest's `pythonpath` option (see
`pyproject.toml`) puts ahead of the repo root on `sys.path`, so `import seqr` resolves to *this*
lightweight stand-in instead of the real app - the same shadowing trick used for the bare
`settings` module `clickhouse_search/backend/base.py` imports directly.

`clickhouse_search`'s live model definitions (`models/search_models.py`,
`models/reference_data_models.py`, which pull in more of `seqr`, e.g. `seqr.models.Dataset` and
`seqr.utils.xpos_utils.CHROMOSOME_CHOICES`) are deliberately NOT needed here: `loading_pipeline`
never imports them (it only ever talks to ClickHouse via raw SQL - see
`lib/test/clickhouse_schema_testcase.py`), and neither does applying `clickhouse_search`'s
migrations (which are self-contained frozen schema snapshots, not built from the live model
classes at apply time). If that ever changes, this stub will need to grow accordingly.
"""
