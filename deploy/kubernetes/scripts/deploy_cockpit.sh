#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

# http://cockpit-project.org/guide/latest/feature-kubernetes.html

if [ "$DELETE_BEFORE_DEPLOY" ]; then
    kubectl delete -f configs/cockpit/cockpit.yaml
fi

kubectl apply -f configs/cockpit/cockpit.yaml

# print username, password for logging into cockpit
kubectl config view
wait_until_pod_is_running cockpit
