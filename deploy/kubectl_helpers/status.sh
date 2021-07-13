#!/usr/bin/env bash

set -x

kubectl cluster-info
kubectl get nodes
kubectl get deployments --all-namespaces
kubectl get services --all-namespaces
kubectl get pods --all-namespaces
kubectl config current-context
