#!/usr/bin/env bash

docker build . -f deploy/docker/hail_search/Dockerfile -t gcr.io/seqr-project/seqr:prototype-hail-search
docker push gcr.io/seqr-project/seqr:prototype-hail-search
