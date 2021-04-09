#!/usr/bin/env bash

# Initializes the seqr database. Needs the following environment variables:
# POSTGRES_PASSWORD, POSTGRES_SERVICE_HOSTNAME.

REFERENCE_DATA_DB_INIT_URL=https://storage.googleapis.com/seqr-reference-data/gene_reference_data_backup.gz

# init seqrdb unless it already exists
export PGHOST=$POSTGRES_SERVICE_HOSTNAME
export PGPASSWORD=$POSTGRES_PASSWORD
if ! psql -U postgres -l | grep seqrdb; then
  psql -U postgres -c 'CREATE DATABASE reference_data_db';
  psql -U postgres reference_data_db <  <(curl -s $REFERENCE_DATA_DB_INIT_URL | gunzip -c -);
  psql -U postgres -c 'CREATE DATABASE seqrdb';

  cd /seqr
  python -u manage.py makemigrations
  python -u manage.py migrate
  python -u manage.py check
  python -u manage.py collectstatic --no-input
  python -u manage.py loaddata variant_tag_types
  python -u manage.py loaddata variant_searches
fi
