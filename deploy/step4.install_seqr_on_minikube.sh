#!/usr/bin/env bash

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

minikube status

set +x
echo ==== deploy all seqr components =====

source venv/bin/activate

./servctl deploy-all --restore-seqrdb-from-backup gs://seqr-reference-data/gene_reference_data.gz minikube

