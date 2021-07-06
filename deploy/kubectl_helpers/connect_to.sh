#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")
trap "kill -- -$$" EXIT

set -x

"${DIR}"/logs.sh "$@" & "${DIR}"/port_forward.sh "$@"
set +x