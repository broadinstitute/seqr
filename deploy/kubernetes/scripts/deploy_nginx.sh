#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

docker build -t ${DOCKER_IMAGE_PREFIX}/nginx  docker/nginx/
if [ "DEPLOY_TO_GOOGLE_CLOUD" = true ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/nginx
fi

kubectl delete -f configs/nginx/nginx-deployment.yaml
kubectl create -f configs/nginx/nginx-deployment.yaml --record

kubectl delete -f configs/nginx/nginx-service.yaml
kubectl create -f configs/nginx/nginx-service.yaml --record
