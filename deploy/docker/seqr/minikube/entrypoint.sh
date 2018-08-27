#!/usr/bin/env bash

set -x

env

echo SHELL: $SHELL
echo PATH: $PATH
echo PYTHONPATH: $PYTHONPATH

# init gcloud
gcloud config set project $GCLOUD_PROJECT
gcloud config set compute/zone $GCLOUD_ZONE

if [ -e "/.config/client_secrets.json" ]; then
    # authenticate to google cloud using service account
    cp /usr/share/zoneinfo/US/Eastern /etc/localtime
    gcloud auth activate-service-account --key-file /.config/client_secrets.json
    cp /.config/boto /root/.boto
fi


# launch django dev server in background
cd /seqr

git pull
git checkout $SEQR_GIT_BRANCH
pip install --upgrade -r requirements.txt  # doublecheck that requirements are up-to-date
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check
python -u manage.py collectstatic --no-input

# launch django server in background
cd /seqr_settings
gunicorn -w 4 -c gunicorn_config.py wsgi:application |& stdbuf -o0 grep -v curl |& tee /var/log/gunicorn.log &

#python manage.py runserver 0.0.0.0:8000 &

# allow pg_dump and other postgres command-line tools to run without having to enter a password
echo "*:*:*:*:$POSTGRES_PASSWORD" > ~/.pgpass
chmod 600 ~/.pgpass


# sleep to keep image running even if gunicorn is killed / restarted
sleep 1000000000000
