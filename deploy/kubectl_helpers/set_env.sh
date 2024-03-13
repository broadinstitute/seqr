#!/usr/bin/env bash

set -x -e

GCLOUD_PROJECT=seqr-project
GCLOUD_ZONE=us-central1-b

DEPLOYMENT_TARGET=$1

case ${DEPLOYMENT_TARGET} in
  dev)
    CLUSTER_NAME=seqr-cluster-dev
    ;;
  prod)
    CLUSTER_NAME=seqr-cluster-prod
    ;;
  *)
    echo "Invalid deployment target '${DEPLOYMENT_TARGET}'"
    exit 1
esac

export KUBECONFIG=~/.kube/config
gcloud config set core/project ${GCLOUD_PROJECT}
gcloud config set compute/zone ${GCLOUD_ZONE}
gcloud container clusters get-credentials --zone=${GCLOUD_ZONE} ${CLUSTER_NAME}

kubectl config set-context $(kubectl config current-context) --namespace=default
