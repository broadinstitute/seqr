#!/usr/bin/env bash

set -x

deployment=$1
component=$2

pod_name=$(./get_resource_name.sh pod ${deployment} ${component})

kubectl exec -it ${pod_name} -- /bin/bash
