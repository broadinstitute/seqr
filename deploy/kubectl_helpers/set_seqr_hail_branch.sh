#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

DEPLOYMENT_TARGET=prototype

POD_NAME=$("${DIR}"/utils/get_pod_name.sh "${DEPLOYMENT_TARGET}" seqr)

kubectl exec "${POD_NAME}" -- git init
kubectl exec "${POD_NAME}" -- git remote add origin https://github.com/broadinstitute/seqr
kubectl exec "${POD_NAME}" -- git checkout -b hail-local
kubectl exec "${POD_NAME}" -- git add .
kubectl exec "${POD_NAME}" -- git -c user.email="seqr@broadinstitute.org" commit -m "image local"
kubectl exec "${POD_NAME}" -- git pull origin hail-backend
