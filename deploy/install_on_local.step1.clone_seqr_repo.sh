#!/usr/bin/env bash


if [ -z "$SEQR_DIR" ]; then

    echo "SEQR_BRANCH environment variable not defined. Please run previous install step(s)."

fi

echo "==== Clone the seqr repo ====="
set -x

export SEQR_BRANCH=master

git clone https://github.com/macarthur-lab/seqr.git
cd seqr/
git checkout $SEQR_BRANCH

set +x