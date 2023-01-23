#!/usr/bin/env bash

set -u

COMPONENT=$1
JSON_PATH=$2

kubectl get pod -l "app.kubernetes.io/name=${COMPONENT}" -o "jsonpath=${JSON_PATH}"
