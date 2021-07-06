#!/usr/bin/env bash

set -e

DIR=$(dirname "$BASH_SOURCE")

"${DIR}"/check_context.sh "$@"

STATUS=$("${DIR}"/get_pod_info.sh "$@" "{.items[0].status.phase}")
if [ "${STATUS}" != "Running" ]; then
    echo "Invalid pod status: ${STATUS}"
    exit 1
fi

"${DIR}"/get_pod_info.sh "$@" "{.items[0].metadata.name}"