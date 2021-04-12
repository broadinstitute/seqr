#!/usr/bin/env bash

set -x -e

DEPLOYMENT_TARGET=$1
DIR=$(dirname $BASH_SOURCE)

set +x
source ${DIR}/utils/load_settings.sh ${DEPLOYMENT_TARGET}
set -x

export KUBECONFIG=~/.kube/config
gcloud config set core/project ${GCLOUD_PROJECT}
gcloud config set compute/zone ${GCLOUD_ZONE}
gcloud container clusters get-credentials --zone=${GCLOUD_ZONE} ${CLUSTER_NAME}

kubectl config set-context $(kubectl config current-context) --namespace=${NAMESPACE}
