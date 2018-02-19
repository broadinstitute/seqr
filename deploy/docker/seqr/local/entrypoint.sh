#!/usr/bin/env bash

set -x

env

echo SHELL: $SHELL
echo PYTHONPATH: $PYTHONPATH


# launch webpack ui dev server in background
#cd /seqr/ui
#npm run start &


# authenticate to google cloud using service account
if [ -e "/.config/client_secrets.json" ]; then
    # init gcloud
    cp /usr/share/zoneinfo/US/Eastern /etc/localtime
    gcloud config set project $GCLOUD_PROJECT
    gcloud config set compute/zone $GCLOUD_ZONE
    gcloud auth activate-service-account --key-file /.config/client_secrets.json


    # set up port-forwarding from localhost:9200 to gcloud elasticsearch instance

    export ELASTICSEARCH_SERVICE_HOSTNAME=localhost
    export ELASTICSEARCH_SERVICE_PORT=9200

    gcloud container clusters get-credentials --zone=us-central1-b $GCLOUD_ELASTICSEARCH_CLUSTER_NAME
    ES_CLIENT_POD=$(kubectl get pods -o jsonpath={.items[0].metadata.name} -l 'name=es-client')

    kubectl port-forward ${ES_CLIENT_POD} ${ELASTICSEARCH_SERVICE_PORT} &

    echo '127.0.0.1 mongo' >> /etc/hosts
    echo '127.0.0.1 elasticsearch' >> /etc/hosts
fi


# launch django dev server in background
cd /seqr

pip install --upgrade -r requirements.txt  # double-check that requirements are up-to-date
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check
python -u manage.py collectstatic --no-input

# launch django dev server in background
cd /seqr_settings
gunicorn -w 4 -c gunicorn_config.py wsgi:application |& tee /var/log/gunicorn.log &

#python manage.py runserver 0.0.0.0:8000 &

# allow pg_dump and other postgres command-line tools to run without having to enter a password
echo "*:*:*:*:$POSTGRES_PASSWORD" > ~/.pgpass
chmod 600 ~/.pgpass


# sleep to keep image running even if gunicorn is killed / restarted
sleep 1000000000000
