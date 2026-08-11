# Seqr Loading Pipeline

[![Code Build](https://github.com/broadinstitute/seqr-loading-pipelines/actions/workflows/unit-tests.yml/badge.svg?branch=main)](https://github.com/broadinstitute/seqr-loading-pipelines/actions/workflows/unit-tests.yml)
[![Docker Build](https://github.com/broadinstitute/seqr-loading-pipelines/actions/workflows/prod-release.yml/badge.svg?branch=main)](https://github.com/broadinstitute/seqr-loading-pipelines/actions/workflows/prod-release.yml)

*This repository contains pipelines and infrastructure for loading genomic data from VCF -> ClickHouse to support queries by the _seqr_ application*

---

## 📁 Repository Structure

### `loading_pipeline/api/`
Contains the interface layer to the _seqr_ application.
- `api/model.py` defines pydantic models for the REST interface.
- `api/app.py` specifies an `aiohttp` webserver that handles load data requests.

### `loading_pipeline/bin/`
Scripts or command-line utilities used for setup or task execution.
- `bin/pipeline_worker.py` — manages asynchronous jobs requested by _seqr_.

### `loading_pipeline/deploy/`
Dockerfiles for the loading pipeline itself & any annotation utilities.
Kubernetes manifests are managed separately in [seqr-helm](https://github.com/broadinstitute/seqr-helm/tree/main/charts/pipeline-runner)

### `loading_pipeline/lib/`
Core logic and shared libraries.
- `annotations` defines hail logic to re-format and standardize fields.
- `methods` wraps hail-defined genomics methods for QC.
- `misc` contains single modules with defined utilities.
	- `misc/clickhouse` hosts the logic that manages the parquet ingestion into ClickHouse itself.
- `core` defines key constants/enums/config.
- `reference_datasets` manages parsing of raw reference sources into hail tables.
- `tasks` specifies the Luigi defined pipeline.  Note that Luigi pipelines are defined by their requirements, so
the pipeline is defined, effectively, in reverse.
	- `WriteClickhouseLoadSuccessFileTask` is the last task, defining a `requires()` method that runs the pipeline either locally or on scalable compute.
	- `WriteImportedCallset` is the first task, importing a VCF into a Hail Matrix table, an "imported callset".
- `test` holds a few utilities used by the tests, which are dispersed throughout the rest of the repository.
- `paths.py` defines paths for all intermediate and output files of the pipeline.

### `loading_pipeline/ops/`
Manual operations scripts.

### `loading_pipeline/var/`
Static configuration and test files.

---

## ⚙️ Setup for Local Development
The production pipeline runs with python `3.11`.

### Clone the repo and install python requirements
```bash
git clone https://github.com/broadinstitute/seqr-loading-pipelines.git
cd seqr-loading-pipelines
RUN uv sync --group dev --locked
```

### [Install](https://clickhouse.com/docs/getting-started/quick-start/oss) & start ClickHouse with provided test configuration:
> **Note:** We are running ClickHouse `26.3.9-lts` in production.
```bash
curl https://clickhouse.com/ | sh
./clickhouse server --config-file=./seqr-loading-pipelines/loading_pipeline/var/clickhouse_config/test-clickhouse.xml
```

### [Run the Tests](https://github.com/broadinstitute/seqr-loading-pipelines/blob/main/.github/workflows/unit-tests.yml#L66-L73)

### Run an Individual Test
```bash
uv run pytest loading_pipeline/lib/misc/math_test.py
```

### Formatting and Linting
```bash
uv run ruff format .
uv run ruff check .
```

## 🚪 Schema Entrypoints
- The expected fields and types are defined in `dataset_type.py` as the `col_fields`, `entry_fields`, and `row_fields` properties.  Examples
of the SNV_INDEL/MITO/SV/GCNV callset schemas may be found in the tests.
- The VEP schema is defined in JSON within the vep*.json config files, then parsed into hail in `lib/annotations/vep.py`.
- Examples of exported parquets may be found in `lib/tasks/exports/*_parquet_test.py`


## 🚶‍♂️ ClickHouse Load Walkthrough
- The Clickhouse Load follows the pattern established in the [Making a Large Data Load Resilient](https://clickhouse.com/blog/supercharge-your-clickhouse-data-loads-part3) blog 
	- Rows are first loaded into a `staging` database that copies the production `TABLE`s and `MATERIALIZED VIEW`s.
	- After all `entries` are inserted, we validate the inserted row count and finalize the per-project allele frequency aggregation.
	- Partitions are atomically moved from the `staging` environment to production. 
