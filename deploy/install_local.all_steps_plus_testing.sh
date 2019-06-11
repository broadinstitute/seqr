#!/usr/bin/env bash

source ~/.bashrc

set -x
cat ~/.bashrc

env 
pwd

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run previous install step."
    exit 1
fi

for script in $(ls ${SEQR_DIR}/deploy/install_local.step[1-9]*)
do

    cd ${SEQR_DIR}/..
    echo Running $script
    source $script

done

echo All install steps completed.
