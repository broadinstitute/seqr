#!/bin/bash

#
# VEP init action for dataproc
#
# adapted/copied from
# https://github.com/broadinstitute/gnomad_methods/blob/main/init_scripts/vep105-init.sh
# and gs://hail-common/hailctl/dataproc/0.2.128/vep-GRCh38.sh
# 
# NB: This is code used for initializing a dataproc cluster and runs as an intialization
# action when the rest of our code is unavailable. 
#

set -x

export PROJECT="$(gcloud config get-value project)"
export DEPLOYMENT_TYPE="$(/usr/share/google/get_metadata_value attributes/DEPLOYMENT_TYPE)"
export REFERENCE_GENOME="$(/usr/share/google/get_metadata_value attributes/REFERENCE_GENOME)"
export PIPELINE_RUNNER_APP_VERSION="$(/usr/share/google/get_metadata_value attributes/PIPELINE_RUNNER_APP_VERSION)"
export REFERENCE_DATASETS_DIR="$(/usr/share/google/get_metadata_value attributes/REFERENCE_DATASETS_DIR)"

# Install docker
apt-get update
apt-get -y install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg2 \
    software-properties-common \
    tabix
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
apt-get update
apt-get install -y --allow-unauthenticated docker-ce

# https://github.com/hail-is/hail/issues/12936
sleep 60
sudo service docker restart

cat >/vep.c <<EOF
#include <unistd.h>
#include <stdio.h>

int
main(int argc, char *const argv[]) {
  if (setuid(geteuid()))
    perror( "setuid" );

  execv("/vep.bash", argv);
  return 0;
}
EOF
gcc -Wall -Werror -O2 /vep.c -o /vep
chmod u+s /vep

gcloud storage cp gs://seqr-pipeline-runner-builds/$DEPLOYMENT_TYPE/$PIPELINE_RUNNER_APP_VERSION/bin/download_vep_reference_data.bash /download_vep_reference_data.bash
chmod +x /download_vep_reference_data.bash
./download_vep_reference_data.bash $REFERENCE_GENOME

gcloud storage cp gs://seqr-pipeline-runner-builds/$DEPLOYMENT_TYPE/$PIPELINE_RUNNER_APP_VERSION/bin/vep /vep.bash
chmod +x /vep.bash

