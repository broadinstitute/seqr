# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Commands

**Python environment setup:**
```bash
pyenv shell 3.11
uv sync --group dev --locked
```

**Run all tests:**
```bash
pyenv shell 3.11
uv run pytest
```

**Run a single test file:**
```bash
pyenv shell 3.11
uv run pytest loading_pipeline/lib/misc/math_test.py
```

**Formatting and linting:**
```bash
pyenv shell 3.11
uv run ruff format .
uv run ruff check .
```

## Project Architecture

This is a genomic data loading pipeline that ingests variant data from VCF files into ClickHouse via Hail and Luigi. The overall flow:

```
VCF Input → Hail Matrix Table → Parquet Files → ClickHouse Staging → Production
```

### Core Components

**`loading_pipeline/lib/tasks/`** — Luigi-based pipeline tasks
- Tasks are defined by their `requires()` method (reverse dependency declaration)
- `RunPipelineTask` is the main entry point that chains together:
  - `WriteMetadataForRunTask` (metadata generation)
  - `UpdateVariantAnnotationsTableWithNewVariantsTask` (annotation updates)
  - `WriteNewEntriesParquetTask` (variant entries → parquet)
  - `WriteNewVariantsParquetTask` (variants → parquet)
  - `WriteNewVariantDetailsParquetTask` (details → parquet)
  - `WriteClickhouseLoadSuccessFileTask` (final atomicity marker)
- Base tasks in `base/` provide shared parameters and utilities

**`loading_pipeline/lib/annotations/`** — Hail-based variant annotation logic
- Standardizes and reformats VEP, gnomAD, and other annotation fields
- VEP schema defined in `vep*.json` files, parsed in `vep.py`

**`loading_pipeline/lib/misc/clickhouse/`** — ClickHouse ingestion
- Manages staging table creation and atomic partition movement to production
- Follows the ["Making a Large Data Load Resilient"](https://clickhouse.com/blog/supercharge-your-clickhouse-data-loads-part3) pattern

**`loading_pipeline/api/`** — REST interface
- `model.py` defines Pydantic schemas for incoming requests
- `app.py` runs an aiohttp server handling load requests

**`loading_pipeline/bin/pipeline_worker.py`** — Job runner
- Manages asynchronous pipeline jobs requested via the REST API

### Schema Definitions

Expected field schemas are defined in `core/dataset_type.py`:
- `col_fields` — variant fields (position, annotation, etc.)
- `entry_fields` — per-sample genotype fields
- `row_fields` — additional row-level metadata

Test files in `lib/tasks/exports/*_test.py` contain examples of the expected parquet export schemas.

## Development Notes

- **Python 3.11 required** — Always activate with `pyenv shell 3.11` before running commands
- **Ruff configuration** — Follows single quotes, 88 char line limit. Test files allow asserts, private access, and high-arity functions
- **ClickHouse tests** — Run locally against a test ClickHouse instance (see README for setup)
- **Tests use pytest** — Not unittest; use `pytest` command directly
