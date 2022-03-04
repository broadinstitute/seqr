#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

kubectl rollout restart deployment/seqr
