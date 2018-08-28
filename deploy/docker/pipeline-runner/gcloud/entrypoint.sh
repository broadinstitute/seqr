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

# sleep to keep image running even if the jupyter notebook is killed / restarted
sleep 1000000000000
