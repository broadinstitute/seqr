#!/usr/bin/env bash


# resize cluster
CLUSTER=$(gcloud dataproc clusters list | cut -f 1 -d \ | grep -v NAME | grep seqr | head -n 1)
if [ -z $CLUSTER ]; then
    echo ERROR: cluster doesn\'t exist
    exit 0
fi

python utils/connect_cluster.py --name $CLUSTER
