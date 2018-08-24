#!/usr/bin/env bash

source /root/.bashrc

cd /hail-elasticsearch-pipelines

python2.7 gcloud_dataproc/submit.py --run-locally "$@"
