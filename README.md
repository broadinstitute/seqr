
seqr
====
![Unit Tests](https://github.com/populationgenomics/seqr/workflows/Unit%20Tests/badge.svg?branch=master) | ![Local Install Tests](https://github.com/populationgenomics/seqr/workflows/local%20install%20tests/badge.svg?branch=master)

seqr is a web-based tool for rare disease genomics.
This repository contains code that underlies the [CPG seqr instance](http://seqr.populationgenomics.org.au).

## Technical Overview

seqr consists of the following components:
- postgres - SQL database used by seqr to store project metadata and user-generated content such as variant notes, etc.
- elasticsearch - NoSQL database used to store variant callsets.
- redis - in-memory cache used to speed up request handling.
- seqr - the main client-server application built using react.js, python and django.
- pipeline-runner - optional container for running hail pipelines to annotate and load new datasets into elasticsearch. If seqr is hosted on google cloud (GKE or GCE), Dataproc spark clusters can be used instead.
- kibana - optional dashboard and visual interface for elasticsearch.

## Install

The seqr production instance runs on Google Kubernetes Engine (GKE) and data is loaded using Google Dataproc Spark clusters. 

On-prem installs can be created using docker-compose:
**[Local installs using docker-compose](deploy/LOCAL_INSTALL.md)**  


## Updating / Migrating an older seqr Instance	

For notes on how to update an older instance, see  	

[Update/Migration Instructions](deploy/MIGRATE.md)

## Development

At the CPG, we don't include the web bundle in the repository anymore, this means you'll need to build the UI before you develop first.

Build UI and link build files back to `static/`:

```bash
cd ui/
npm install
npm run build
ln dist/app* ../static
cd ..
```

Start Python server:

```bash
gunicorn -c deploy/docker/seqr/config/gunicorn_config.py wsgi:application
```

### Developing UI

If you're developing UI, you can run a hot-reload UI server. You'll need to start the Python server first (using gunicorn), then run:

```bash
cd ui/
npm run start
```

Then visit https://localhost:3000 in your browser to access the hot-reloadable version of seqr. All requests are proxied back to to Python backend.

### Common errors

- `Error occured while trying to proxy to: localhost:3000`: You didn't start the Python backend server.
- `TemplateDoesNotExist at / app.html`: then it might say something like: `/Users/${USER}/source/seqr/ui/dist/app.html (Source does not exist)`, you'll need to make sure the `app.html` file is available in `ui/dist/`.
