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

if [ -e "/.config/service-account-key.json" ]; then
    # authenticate to google cloud using service account
    cp /usr/share/zoneinfo/US/Eastern /etc/localtime
    # this is error prone, retry up to 5 times, 10 seconds in between
    retries=0
    until [ "$retries" -ge 5 ]
    do
        gcloud auth activate-service-account --key-file /.config/service-account-key.json && break
        retries=$((retries+1))
        echo "gcloud auth failed. Retrying, attempt ${retries}/5"
        sleep 10
    done
    
    cp /.config/boto /root/.boto
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

# init and populate seqrdb unless it already exists
if ! psql --host "$POSTGRES_SERVICE_HOSTNAME" -U "$POSTGRES_USERNAME" -l | grep seqrdb; then
    psql --host "$POSTGRES_SERVICE_HOSTNAME" -U "$POSTGRES_USERNAME" -c 'CREATE DATABASE reference_data_db';
    psql --host "$POSTGRES_SERVICE_HOSTNAME" -U "$POSTGRES_USERNAME" -c 'CREATE DATABASE seqrdb';
    python -u manage.py migrate
    python -u manage.py migrate --database=reference_data
    python -u manage.py loaddata variant_tag_types
    python -u manage.py loaddata variant_searches
    python -u manage.py update_all_reference_data --use-cached-omim
else
    # run any pending migrations if the database already exists
    python -u manage.py migrate
    python -u manage.py migrate --database=reference_data
fi

python -u manage.py check

# launch django server in background
/usr/local/bin/start_server.sh

# sleep to keep image running even if gunicorn is killed / restarted
sleep 1000000000000
