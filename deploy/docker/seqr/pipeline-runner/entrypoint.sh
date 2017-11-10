#!/usr/bin/env bash

set -x

env

if [ "$DEPLOY_TO" = 'local' ]
then
    # wait for drive to be mounted
    while [ ! -f /seqr/manage.py ]
    do
        echo "Error: /seqr/manage.py doesn't exist. It may just not have been mounted yet..."

        sleep 5
    done

    ls -la1 /seqr/
fi

source ~/.bashrc_custom

echo SHELL: $SHELL
echo PYTHONPATH: $PYTHONPATH

# init gcloud
gcloud config set project $GCLOUD_PROJECT
gcloud config set compute/zone $GCLOUD_ZONE


# launch jupyter notebook in background
nohup jupyter notebook --ip=0.0.0.0 --port=35000 --allow-root &

# launch django dev server in background
cd /seqr

pip install --upgrade -r requirements.txt
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check

# launch django dev server in background
cd /seqr_settings

#python manage.py runserver 0.0.0.0:8000 &

# sleep to keep image running even if gunicorn is killed / restarted
sleep 1000000000000
