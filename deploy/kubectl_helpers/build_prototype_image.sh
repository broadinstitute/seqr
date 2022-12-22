#!/usr/bin/env bash

docker build . -f deploy/docker/seqr/Dockerfile --platform=linux/amd64 -t gcr.io/seqr-project/seqr:prototype
docker push gcr.io/seqr-project/seqr:prototype
