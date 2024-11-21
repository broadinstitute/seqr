#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

COMPONENT=$2

POD_NAME=$("${DIR}"/utils/get_pod_name.sh "$@")

kubectl exec -it "${POD_NAME}" -c "${COMPONENT}" -- /bin/bash
