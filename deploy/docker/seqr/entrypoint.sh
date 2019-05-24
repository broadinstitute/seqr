#!/usr/bin/env bash

set -x

env

echo SHELL: $SHELL
echo PATH: $PATH
echo PYTHONPATH: $PYTHONPATH

# init gcloud
if [ $GCLOUD_PROJECT ]; then
    gcloud config set project $GCLOUD_PROJECT
fi

if [ $GCLOUD_ZONE ]; then
    gcloud config set compute/zone $GCLOUD_ZONE
fi

if [ -e "/.config/service-account-key.json" ]; then
    # authenticate to google cloud using service account
    cp /usr/share/zoneinfo/US/Eastern /etc/localtime
    gcloud auth activate-service-account --key-file /.config/service-account-key.json
    cp /.config/boto /root/.boto
fi

# link to persistent disk dir with static files
mkdir -p /seqr_static_files/generated_files
ln -s /seqr_static_files/generated_files /seqr_settings/generated_files

# launch django dev server in background
cd /seqr

# git pull
git checkout $SEQR_GIT_BRANCH
pip install --upgrade -r requirements.txt  # doublecheck that requirements are up-to-date
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check
python -u manage.py collectstatic --no-input
python -u manage.py loaddata variant_tag_types
python -u manage.py loaddata variant_searches


# launch django server in background
/usr/local/bin/start_server.sh

# allow pg_dump and other postgres command-line tools to run without having to enter a password
echo "*:*:*:*:$POSTGRES_PASSWORD" > ~/.pgpass
chmod 600 ~/.pgpass

if [ $ENABLE_DATABASE_BACKUPS ]; then
    # set up cron database backups
    echo 'SHELL=/bin/bash
0 0 * * * python -u manage.py run_settings_backup.py --deployment-type $DEPLOYMENT_TYPE >> /var/log/cron.log
0 */4 * * * python -u manage.py run_postgres_database_backup.py --deployment-type $DEPLOYMENT_TYPE >> /var/log/cron.log
0 0 * * 0 python -u manage.py update_omim --omim-key $OMIM_KEY >> /var/log/cron.log
0 0 * * 0 python -u manage.py update_human_phenotype_ontology >> /var/log/cron.log
' | crontab -

    env > /etc/environment  # this is necessary for crontab commands to run with the right env. vars.

    /etc/init.d/cron start
fi


# sleep to keep image running even if gunicorn is killed / restarted
sleep 1000000000000
