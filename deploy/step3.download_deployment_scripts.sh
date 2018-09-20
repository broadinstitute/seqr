#!/usr/bin/env bash

echo ==== download seqr deployment code, install python dependencies =====
set -x

export SEQR_BRANCH=linux-install-improvements

git clone https://github.com/macarthur-lab/seqr.git
cd seqr/
git checkout $SEQR_BRANCH

curl -Lo virtualenv-16.0.0.tar.gz https://pypi.python.org/packages/source/v/virtualenv/virtualenv-16.0.0.tar.gz
tar xzf virtualenv-16.0.0.tar.gz
python virtualenv-16.0.0/virtualenv.py --python=python2.7 venv
source venv/bin/activate

pip install -r deploy/deploy-requirements.txt

echo "source venv/bin/activate" > activate_virtualenv.sh
chmod 666 activate_virtualenv.sh  # this script must be sourced rather than executed

set +x