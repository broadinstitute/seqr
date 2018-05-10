#!/usr/bin/env bash

set -x

env

echo SHELL: $SHELL
echo PYTHONPATH: $PYTHONPATH

# init gcloud
gcloud config set project $GCLOUD_PROJECT
gcloud config set compute/zone $GCLOUD_ZONE

if [ -e "/.config/client_secrets.json" ]; then
    # init gcloud
    cp /usr/share/zoneinfo/US/Eastern /etc/localtime
    gcloud config set project $GCLOUD_PROJECT
    gcloud config set compute/zone $GCLOUD_ZONE
    gcloud auth activate-service-account --key-file /.config/client_secrets.json
    cp /.config/boto /root/.boto
fi

# launch django dev server in background
cd /seqr

git pull
git checkout $SEQR_GIT_BRANCH
pip install --upgrade -r requirements.txt  # double-check that requirements are up-to-date
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check
python -u manage.py collectstatic --no-input

# launch django dev server in background
cd /seqr_settings
gunicorn -w 4 -c gunicorn_config.py wsgi:application |& stdbuf -o0 grep -v curl |& tee /var/log/gunicorn.log &

# allow pg_dump and other postgres command-line tools to run without having to enter a password
echo "*:*:*:*:$POSTGRES_PASSWORD" > ~/.pgpass
chmod 600 ~/.pgpass

# set up cron database backups
echo 'SHELL=/bin/bash
0 0 * * * python /mounted-bucket/settings_backups/run_settings_backup.py >& /var/log/cron.log
0 0 * * * python /seqr/manage.py update_projects_in_new_schema -w /seqr/wgs_projects.txt 2>&1 >> /var/log/cron.log
0 0 * * * python /seqr/manage.py transfer_gene_lists 2>&1 >> /var/log/cron.log
0 */4 * * * python /mounted-bucket/database_backups/run_postgres_database_backup.py 2>&1 >> /var/log/cron.log
' | crontab -

env > /etc/environment  # this is necessary for crontab commands to run with the right env. vars.

/etc/init.d/cron start

# sleep to keep image running even if gunicorn is killed / restarted
sleep 1000000000000
