#!/usr/bin/env bash

if [ -z $1 ]; then
    CLUSTER=$(gcloud dataproc clusters list | cut -f 1 -d \ | grep -v NAME | grep seqr | head -n 1)
else
    CLUSTER=$1
fi

if [ -z $CLUSTER ]; then
    echo ERROR: cluster doesn\'t exist
    exit 0
fi

gcloud dataproc clusters delete $CLUSTER
