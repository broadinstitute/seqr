#!/usr/bin/env bash

REFERENCE_DATA_DB_INIT_URL=https://storage.googleapis.com/seqr-reference-data/gene_reference_data_backup.gz

echo SHELL: $SHELL
echo PATH: $PATH
echo PYTHONPATH: $PYTHONPATH

echo $GSA_KEY > /tmp/gsa-key.json
gcloud auth activate-service-account --key-file /tmp/gsa-key.json
rm /tmp/gsa-key.json

# link to persistent disk dir with static files
mkdir -p /seqr_static_files/generated_files

# launch django dev server in background
cd /seqr

# allow pg_dump and other postgres command-line tools to run without having to enter a password
echo "*:*:*:*:$POSTGRES_PASSWORD" > ~/.pgpass
chmod 600 ~/.pgpass

# init seqrdb unless it already exists
if ! psql --host $POSTGRES_SERVICE_HOSTNAME -U postgres -l | grep seqrdb; then

  psql --host $POSTGRES_SERVICE_HOSTNAME -U postgres -c 'CREATE DATABASE reference_data_db';
  psql --host $POSTGRES_SERVICE_HOSTNAME -U postgres reference_data_db <  <(curl -s $REFERENCE_DATA_DB_INIT_URL | gunzip -c -);

  psql --host $POSTGRES_SERVICE_HOSTNAME -U postgres -c 'CREATE DATABASE seqrdb';
  python -u manage.py makemigrations
  python -u manage.py migrate
  python -u manage.py check
  python -u manage.py collectstatic --no-input
  python -u manage.py loaddata variant_tag_types
  python -u manage.py loaddata variant_searches

fi

# launch django server in background
/usr/local/bin/start_server.sh