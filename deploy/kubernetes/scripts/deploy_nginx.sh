#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

kubectl delete -f configs/nginx/nginx-ingress.${DEPLOY_TO_PREFIX}.yaml
kubectl create -f configs/nginx/nginx-ingress.${DEPLOY_TO_PREFIX}.yaml

kubectl delete -f configs/nginx/nginx-controller.yaml  # .${DEPLOY_TO}
kubectl create -f configs/nginx/nginx-controller.yaml  # .${DEPLOY_TO}

if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]; then
    kubectl delete -f configs/nginx/nginx-service.${DEPLOY_TO_PREFIX}.yaml
    kubectl create -f configs/nginx/nginx-service.${DEPLOY_TO_PREFIX}.yaml
fi


# wait for pod to start
set +x
while [ ! "$( kubectl get pods | grep 'nginx-' | grep Running)" ] || [ "$( kubectl get pods | grep 'nginx-' | grep Terminating)" ]; do
    echo $(date) - Waiting for nginx pod to enter "Running" state. Current state is: "$( kubectl get pods | grep 'nginx-' )"
    sleep 5
done
echo $(date) - Success. Current state is: "$( kubectl get pods | grep 'nginx-' )"
set -x

