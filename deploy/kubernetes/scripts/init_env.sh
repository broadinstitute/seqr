#!/usr/bin/env bash

if [ -z "$STARTED_VIA_SEQRCTL" ]; then
    echo 'Environment variables not set. Please use seqrctl script to run these commands.'
    exit 1
fi

function wait_until_pod_is_running {

    set +x
    if [ ! $1 ]; then
        echo ERROR: pod label arg not specified
        exit -1
    fi

    # wait for pod to start
    while [ ! "$( kubectl get pods | grep "${1}-" | grep Running )" ] || [ "$( kubectl get pods | grep "${1}-" | grep Terminating)" ]; do
        echo $(date) - Waiting for ${1} pod to enter "Running" state. Current state is: "$( kubectl get pods | grep ${1}- )"
        sleep 5
    done
    echo $(date) - Success. Current state is: "$( kubectl get pods | grep ${1}- )"
    set -x
}

function wait_until_pod_terminates {

    set +x
    if [ ! $1 ]; then
        echo ERROR: pod label arg not specified
        exit -1
    fi

    # wait for pod to terminate
    while [ "$( kubectl get pods | grep "${1}-" | grep Running)" ] || [ "$( kubectl get pods | grep "${1}-" | grep Terminating)" ]; do
        echo $(date) - Waiting for ${1} pod to terminate. Current state is: "$( kubectl get pods | grep ${1}- )"
        sleep 5
    done
    echo $(date) - Done. Current state is: "$( kubectl get pods | grep '${1}-' )"
    set -x
}
