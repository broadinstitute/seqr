#!/usr/bin/env bash

DEPLOYMENT_TARGET=$1
DIR=$(dirname $BASH_SOURCE)

if [[ ! -f ${DIR}/../envs/${DEPLOYMENT_TARGET}.env ]] ; then
    echo "Invalid deployment target '${DEPLOYMENT_TARGET}'"
    exit 1
fi

export $(grep -v '^#' ${DIR}/../envs/shared.env | xargs)
export $(grep -v '^#' ${DIR}/../envs/${DEPLOYMENT_TARGET}.env | xargs)
