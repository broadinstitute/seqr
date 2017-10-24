#!/usr/bin/env bash

set -x

env

echo SHELL: $SHELL
echo PYTHONPATH: $PYTHONPATH

# init gcloud
gcloud config set project $GCLOUD_PROJECT
gcloud config set compute/zone $GCLOUD_ZONE

# launch django dev server in background
cd /seqr

git pull
pip install --upgrade -r requirements.txt

python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check
python -u manage.py collectstatic --no-input

# launch django dev server in background
cd /seqr_settings
gunicorn -w 4 -c gunicorn_config.py wsgi:application |& tee /var/log/gunicorn.log &

# allow pg_dump and other postgres command-line tools to run without having to enter a password
echo "*:*:*:*:$POSTGRES_PASSWORD" > ~/.pgpass
chmod 600 ~/.pgpass

#touch /tmp/ready

# set up cron database backups
echo 'SHELL=/bin/bash
0 */4 * * * python /mounted-bucket/database_backups/run_postgres_database_backup.py
0 0 * * * python /mounted-bucket/settings_backups/run_settings_backup.py
0 0 * * * python /seqr/manage.py update_projects_in_new_schema
0 0 * * * python /seqr/manage.py transfer_gene_lists
' | crontab -

/etc/init.d/cron start

# sleep to keep image running even if gunicorn is killed / restarted
sleep 1000000000000
