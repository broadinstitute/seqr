#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

POD_NAME=$("${DIR}"/utils/get_pod_name.sh "$@")

kubectl logs -f "${POD_NAME}" --all-containers
