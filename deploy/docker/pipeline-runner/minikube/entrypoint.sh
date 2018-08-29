#!/usr/bin/env bash

set -x

env

source ~/.bashrc

# init gcloud
gcloud config set project $GCLOUD_PROJECT
gcloud config set compute/zone $GCLOUD_ZONE

if [ -e "/.config/service-account-key.json" ]; then
    # authenticate to google cloud using service account
    cp /usr/share/zoneinfo/US/Eastern /etc/localtime
    gcloud auth activate-service-account --key-file /.config/service-account-key.json
    cp /.config/boto /root/.boto
fi

# launch jupyter notebook in background
mkdir /ipython_notebooks
cd /ipython_notebooks
nohup jupyter notebook --ip=0.0.0.0 --port=30005 --allow-root --NotebookApp.token='' &

# sleep to keep image running even if the jupyter notebook is killed / restarted
sleep 1000000000000
