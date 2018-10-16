#!/usr/bin/env bash

set +x
echo ==== Clone the seqr repo =====
set -x


if [ -z "$SEQR_DIR" ]; then

    export SEQR_BRANCH=master

    git clone https://github.com/macarthur-lab/seqr.git
    cd seqr/
    git checkout $SEQR_BRANCH

    export PLATFORM=$(python - <<EOF
import platform
p = platform.platform().lower()
if "centos" in p: print("centos")
elif "ubuntu" in p: print("ubuntu")
elif "darwin" in p: print("macos")
else: print("unknown")
EOF
)

    export SEQR_DIR=$(pwd)
    echo '
# ---- seqr install -----
export PLATFORM='${PLATFORM}'
export SEQR_DIR='${SEQR_DIR}'
' >> ~/.bashrc

    cd ..
fi
