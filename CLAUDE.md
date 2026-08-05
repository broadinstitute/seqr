# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

seqr is a web-based rare disease genomics tool (Broad Institute): Django (Python) server + React (JS) client, backed by **postgres** (`seqrdb` + `reference_data_db`), **clickhouse** (variant search, read-only from the app), and optional **redis** cache. Dataset loading is done by an external pipeline-runner service (not in this repo). Elasticsearch and Hail-backend search are deprecated in favor of ClickHouse — don't build new features against ES.

## Commands

**Backend:** `pip install -r requirements-dev.txt -r requirements.txt`, `./manage.py migrate`, `./manage.py migrate --database=reference_data`, `./manage.py runserver`

Run all backend tests (matches CI): `./manage.py test -p '*_tests.py' reference_data clickhouse_search seqr matchmaker panelapp`
Single test: `./manage.py test seqr.views.apis.family_api_tests.FamilyAPITest.test_update_family`
`clickhouse_search` tests need a running ClickHouse + `CLICKHOUSE_READER_USER`/`CLICKHOUSE_WRITER_USER`/`CLICKHOUSE_SERVICE_HOSTNAME`. CI enforces `--fail-under=99` coverage.

**Frontend (`ui/`):** `npm install`, `npm run start` (dev server), `npm run build`, `npm test`, `npm run lint`
Single test: `npx jest path/to/File.test.js`. Coverage threshold 40% lines/statements. Node 14 required.

## Architecture

- **`seqr/`** — core app (users, projects, families, samples, saved variants, permissions). `models.py` is the central data model. Function-based views (no DRF) in `views/apis/*.py`, one module per resource, each paired with `*_tests.py`, wired by name in `urls.py`. No service layer — logic lives in `views/apis`/`utils/`.
- **`reference_data/`** — external gene/variant reference datasets (OMIM, gencode, HPO, PanelApp, etc.), lives in the separate `reference_data` Postgres DB via `ReferenceDataRouter`; refreshed by `update_all_reference_data`.
- **`matchmaker/`** — GA4GH Matchmaker Exchange (MME) protocol (`views/external_api.py`) plus seqr's own MME UI endpoints (`views/matchmaker_api.py`).
- **`panelapp/`** — Genomics England PanelApp gene panel integration.
- **`clickhouse_search/`** — the variant search backend (sole supported implementation; ES only remains in old migrations). Custom Django DB backend (`backend/`), ClickHouse-side models (`models/`), query construction in `search.py`/`managers.py` called from `seqr`'s `variant_search_api.py`. Routed via `ClickHouseRouter`.
- **`vlm/`** — separate standalone `aiohttp` service (own requirements, own Auth0 auth), not part of the Django URLconf, deployed independently.

**DB routing:** four connections — `default` (seqrdb), `reference_data`, `clickhouse`/`clickhouse_write` — via `DATABASE_ROUTERS`. No cross-DB joins at the DB level.

**Auth:** Google OAuth2 / Azure AD v2 via `social_django`, plus `django-guardian` object-level permissions.

### Frontend (`ui/`)

- `app.jsx` entry: Redux `Provider` + react-router-dom v5.
- `pages/<Page>/` — one dir per route, each with `X.jsx`, `reducers.js`, `selectors.js`(+`.test.js`), `constants.js`, `fixtures.js`, `components/`.
- `shared/` — cross-page components/utils. `redux/` — classic ducks pattern, `redux/utils/reducerFactories.js` for generic reducers.
- Module aliases via `babel-plugin-module-resolver`: `shared -> ./shared/`, `pages -> ./pages/`.
- Semantic UI React + `styled-components`. Codebase is mostly JS/JSX; **new files should be written in TypeScript**.
- Jest + Enzyme, colocated `*.test.js`. Prefer deep-rendering connected components over shallow-rendering unconnected ones in tests.


## Development Notes

Never delete a file that is not in source control without confirming first
