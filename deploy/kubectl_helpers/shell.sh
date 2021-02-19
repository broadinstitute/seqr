#!/usr/bin/env bash

set -x

DEPLOYMENT_TARGET=$1
COMPONENT=$2

POD_NAME=$(./get_resource_name.sh pod ${DEPLOYMENT_TARGET} ${COMPONENT})

kubectl exec -it ${POD_NAME} -- /bin/bash
