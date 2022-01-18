#!/usr/bin/env bash

set -x -e

BUILD_VERSION=$1

gsuitl -m cp -r /seqr-reference-data/GRCh${BUILD_VERSION} ${GS_BUCKET}/reference_data/GRCh${BUILD_VERSION}