#!/usr/bin/env bash

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run previous install step(s)."
    exit 1
fi

set +x
echo ==== install seqr python dependencies used during deployment =====
set -x

cd ${SEQR_DIR}

curl -Lo virtualenv-16.0.0.tar.gz https://pypi.python.org/packages/source/v/virtualenv/virtualenv-16.0.0.tar.gz
tar xzf virtualenv-16.0.0.tar.gz
python virtualenv-16.0.0/virtualenv.py --python=python2.7 venv
source venv/bin/activate

pip install -r deploy/deploy-requirements.txt

echo "source venv/bin/activate" > activate_virtualenv.sh
chmod 666 activate_virtualenv.sh  # this script must be sourced rather than executed

set +x
