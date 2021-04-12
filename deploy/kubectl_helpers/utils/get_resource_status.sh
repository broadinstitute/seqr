#!/usr/bin/env bash

DIR=$(dirname $BASH_SOURCE)
${DIR}/get_resource_info.sh "$@" "{.items[0].status.phase}"
