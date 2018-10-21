#!/usr/bin/env bash

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run previous install step."
    exit 1
fi

for script in $(ls ${SEQR_DIR}/deploy/install_local.step*)
do

    cd ${SEQR_DIR}/..
    echo Running $script
    source $script

done