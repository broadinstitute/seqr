# seqr local development set up

Instructions for setting up seqr on a local machine for development

## Install dependencies

Before installing, always check first to see if a dependency is already installed.

- [python 3](https://www.python.org/downloads/)

- [gcloud](https://cloud.google.com/sdk/install)

- [postgres](https://www.postgresql.org/download/)
  - Note: if you use homebrew to install postgres, it may not create the correct superuser. 
After installation, run `psql -l` and if there is no user named `postgres`, run the following:
  `$POSTGRES_INSTALL_PATH/bin/createuser -s postgres`

- [redis](https://redis.io/topics/quickstart)

- [node/npm <14](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm).  Note: more recent versions of `node` may not function are not officially supported.

Optionally, if planning to use elasticsearch from docker-compose, install:
- [docker](https://docs.docker.com/install/)
- [docker-compose](https://docs.docker.com/compose/install/)   

If installing for the Broad instance/ other kubernetes deployments, install:
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/)

## Install seqr

```bash
git clone https://github.com/broadinstitute/seqr.git
    
cd ./seqr
pip install -r requirements-dev.txt
pip install -r requirements.txt
    
cd ./ui/
npm install
```

### Setup postgres database

#### Broad seqr instance

If you are developing for the Broad's seqr instance, copy the production database to your local 
database so the data looks comparable. You will want to periodically re-run this to keep in sync.

```bash
./deploy/kubectl_helpers/set_env.sh prod 
./deploy/kubectl_helpers/restore_local_db.sh prod seqrdb
./deploy/kubectl_helpers/restore_local_db.sh prod reference_data_db
```
Note: If either database restore script fails due to the `gcloud sql export` command taking longer than expected,
you can update the `FILENAME` property in the script to match an existing export, comment out the `gcloud sql export`
line, and re-run the script.

#### Stand alone seqr instance

If you are developing seqr locally without access to an existing instance 
(i.e. you want to add a feature but don't otherwise host your own seqr), run the following

```bash
psql -U postgres -c 'CREATE DATABASE reference_data_db';
psql -U postgres -c 'CREATE DATABASE seqrdb';    
    
./manage.py migrate
./manage.py migrate --database=reference_data
./manage.py check
./manage.py loaddata variant_tag_types
./manage.py loaddata variant_searches
./manage.py update_all_reference_data --use-cached-omim
./manage.py createsuperuser
```

### Set bash profile - Broad developers only

This is not required, but it can be helpful to set several environment variables in your bash profile to ensure seqr
always starts up with the correct configuration.  

```bash
# Mirrors production configuration
export INTERNAL_NAMESPACES=gregor-consortium,seqr-access
export ANALYST_USER_GROUP=TGG_Users
export PM_USER_GROUP=TGG_PM
    
# Set the client ID and secret for the seqr-local OAuth client (from GCP)
# Note: do not use the values from `seqr-secrets` in secret manager, the local credentials are saved [here](https://console.cloud.google.com/apis/credentials?project=seqr-project).
export SOCIAL_AUTH_GOOGLE_OAUTH2_CLIENT_ID=
export SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=   
    
# Set if planning to tunnel to production Airtable or Elasticsearch (from secrets backup)
export AIRTABLE_API_KEY=
export SEQR_ES_PASSWORD=
```

## Run seqr

In order to run seqr, you need to have 2 servers running simultaneously, one for the client-side javascript and one
for the server-side python
 
### Prerequisites
Before running seqr, make sure the following are currently running/ started:

- postgres

- redis (optional, improves performance but only needed  when actively developing cache-related code)

- elasticsearch (optional, only needed when actively developing search functionality) 
  - Since seqr accesses ES as read-only, it is safe to tunnel to production data during local development. 
  This is the easiest approach if you want representative data
    ```bash
    ./deploy/kubectl_helpers/connect_to.sh prod elasticsearch
    ```
    
  - If you want ES running but do not need production data/ are working with a standalone seqr instance, 
  use docker-compose
    ```bash
    docker compose up elasticsearch
    ```
    
### Run ui asset server

Run asset server for javascript and css
```bash
cd ./ui
npm run start
```
 
### Run python/ django server
```bash
./manage.py runserver
```

### Run unit tests

Unit tests are run automatically when code is PR'd to seqr. To run locally, run
```bash
# Server side tests
./manage.py test -p '*_tests.py' reference_data seqr matchmaker panelapp
  
# Client side tests
cd ./ui
npm run test
```
