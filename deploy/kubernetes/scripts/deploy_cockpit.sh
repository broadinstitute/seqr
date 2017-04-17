#!/usr/bin/env bash

set -x

kubectl delete -f configs/cockpit/kubernetes-cockpit.json
kubectl create -f configs/cockpit/kubernetes-cockpit.json


# print username, password for logging into cockpit
kubectl config view

set +x

while [ ! "$( kubectl get pods | grep 'cockpit-' | grep Running )" ] || [ "$( kubectl get pods | grep 'cockpit-' | grep Terminating)" ]; do
    echo $(date) - Waiting for cockpit pod to enter "Running" state. Current state is: "$( kubectl get pods | grep 'cockpit-' )"
    sleep 5
done
echo $(date) - Success. Current state is: "$( kubectl get pods | grep 'cockpit-' )"