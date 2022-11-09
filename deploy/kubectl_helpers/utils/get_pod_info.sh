#!/usr/bin/env bash

set -u

kubectl get pod -l "app.kubernetes.io/name=${COMPONENT}" -o "jsonpath=${JSON_PATH}"
