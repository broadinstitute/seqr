#!/usr/bin/env bash

set -x -e

kubectl rollout restart deployment/seqr
