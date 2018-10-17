#!/usr/bin/env bash


if [ -z "$SEQR_DIR" ]; then

    export SEQR_DIR=$(pwd)/seqr
    echo 'export SEQR_DIR='${SEQR_DIR} >> ~/.bashrc
    echo 'export PYTHONPATH='${SEQR_DIR}':'${SEQR_DIR}'/seqr_settings:$PYTHONPATH' >> ~/.bashrc

fi

if [ -z "$PLATFORM" ]; then

    export PLATFORM=$(python - <<EOF
import platform
p = platform.platform().lower()
if "centos" in p: print("centos")
elif "ubuntu" in p: print("ubuntu")
elif "darwin" in p: print("macos")
else: print("unknown")
EOF
)
    echo 'export PLATFORM='${PLATFORM} >> ~/.bashrc

fi