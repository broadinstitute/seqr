#!/usr/bin/env bash

DEPLOYMENT_TARGET=$1

if [[ ! -f ./envs/${DEPLOYMENT_TARGET}.env ]] ; then
    echo "Invalid deployment target '${DEPLOYMENT_TARGET}'"
    exit 1
fi

export $(grep -v '^#' ./envs/shared.env | xargs)
export $(grep -v '^#' ./envs/${DEPLOYMENT_TARGET}.env | xargs)
