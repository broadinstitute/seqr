#!/usr/bin/env bash

set -x

env

echo SHELL: "$SHELL"
echo PATH: "$PATH"
echo PYTHONPATH: "$PYTHONPATH"

# init gcloud
if [ "$GCLOUD_PROJECT" ]; then
    gcloud config set project "$GCLOUD_PROJECT"
fi

if [ "$GCLOUD_ZONE" ]; then
    gcloud config set compute/zone "$GCLOUD_ZONE"
fi

cd /seqr

# allow pg_dump and other postgres command-line tools to run without having to enter a password
echo "*:*:*:*:$POSTGRES_PASSWORD" > ~/.pgpass
chmod 600 ~/.pgpass
cat ~/.pgpass

# wait for database connectivity, exit if we don't get it within ~2 minutes
pg_retries=0
until [ "$pg_retries" -ge 10 ]
do
    pg_isready -d postgres -h "$POSTGRES_SERVICE_HOSTNAME" -U "$POSTGRES_USERNAME" && break
    pg_retries=$((pg_retries+1))
    if [ "$pg_retries" -eq 10 ]; then
        echo "Postgres database wasn't available after 10 connection attempts"
        exit 1
    else
        echo "Unable to connect to postgres, retrying. Attempt ${pg_retries}/10"
        sleep 12
    fi
done

# run any pending migrations and load missing data
python -u manage.py migrate
python -u manage.py migrate --database=reference_data
python -u manage.py loaddata variant_searches
python -u manage.py loaddata variant_tag_types

python -u manage.py check

# launch django server in background
/usr/local/bin/start_server.sh

# sleep to keep image running even if gunicorn is killed / restarted
sleep 1000000000000
