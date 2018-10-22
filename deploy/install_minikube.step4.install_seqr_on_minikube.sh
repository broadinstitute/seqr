#!/usr/bin/env bash

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run previous install step(s)."
    exit 1
fi

echo ==== Wait for minikube to start =====
set -x

for i in {1..150}; do    # timeout for 5 minutes
   kubectl get po &> /dev/null
   if [ $? -ne 1 ]; then
      break
  fi
  echo 'Waiting for minikube to start...'
  sleep 2
done

sudo minikube addons disable dashboard    # disable kuberentes dashboard to conserve resources

minikube status


set +x
echo ==== install seqr python deployment dependencies =====
set -x

cd ${SEQR_DIR}

curl -Lo virtualenv-16.0.0.tar.gz https://pypi.python.org/packages/source/v/virtualenv/virtualenv-16.0.0.tar.gz
tar xzf virtualenv-16.0.0.tar.gz
python virtualenv-16.0.0/virtualenv.py --python=python2.7 venv

echo "source venv/bin/activate" > activate_virtualenv.sh
chmod 666 activate_virtualenv.sh  # this script must be sourced rather than executed
source activate_virtualenv.sh

pip install -r deploy/deploy-requirements.txt


set +x
echo ==== deploy all seqr components =====
set -x

wget -N https://storage.googleapis.com/seqr-reference-data/gene_reference_data_backup.gz
./servctl deploy-all --restore-seqr-db-from-backup gene_reference_data_backup.gz --docker-image-tag release_20180926 minikube

set +x