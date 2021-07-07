#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

POD_NAME=$("${DIR}"/utils/get_pod_name.sh "$@")

kubectl exec -it "${POD_NAME}" -- /bin/bash
