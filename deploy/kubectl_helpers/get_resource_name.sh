#!/usr/bin/env bash

resource_type=$1
deployment=$2
component=$3

kubectl get ${resource_type} -l name=${component},deployment=gcloud-${deployment} -o jsonpath="{.items[0].metadata.name}"
