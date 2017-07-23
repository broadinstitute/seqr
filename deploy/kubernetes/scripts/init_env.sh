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

    NAME=$1

    # wait for pod to start
    while [ "$(get_pod_status $NAME)" != "Running" ] || [ "$(get_pod_status $NAME)" = "Terminating" ]; do
        echo $(date) - Waiting for ${1} pod to enter "Running" state. Current state is: "$( kubectl get pods | grep ${1}- )"
        sleep 5
    done
    echo $(date) - Success. Current state is: "$(get_pod_status $NAME)"
    set -x
}

function wait_until_pod_terminates {

    set +x
    if [ ! $1 ]; then
        echo ERROR: pod label arg not specified
        exit -1
    fi

    NAME=$1

    # wait for pod to terminate
    while [ "$(get_pod_status $NAME)" = "Running" ] || [ "$(get_pod_status $NAME)" = "Terminating" ]; do
        echo $(date) - Waiting for ${1} pod to terminate. Current state is: "$(get_pod_status $NAME)"
        sleep 5
    done
    echo $(date) - Done. Current state is: $POD_STATUS
    set -x
}

function get_pod_status {
    if [ ! $1 ]; then
        echo ERROR: name arg not passed to get_pod_status function.
        exit -1
    fi

    NAME=$1

    echo "$( kubectl get pods -l deployment=${DEPLOY_TO} -l name=${NAME} -o jsonpath={.items[0].status.phase} )"
}

function get_pod_name {
    if [ ! $1 ]; then
        echo ERROR: name arg not passed to get_pod_name function.
        exit -1
    fi

    NAME=$1

    echo "$( kubectl get pods -l name=${NAME} -o jsonpath={.items[0].metadata.name} )"

}


function get_node_name {
    if [ ! $1 ]; then
        echo ERROR: name arg not passed to get_pod_name function.
        exit -1
    fi

    NAME=$1

    echo "$( kubectl get nodes -o jsonpath={.items[0].metadata.name} )"

}