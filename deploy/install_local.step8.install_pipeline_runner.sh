#!/usr/bin/env bash

set +x

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run install_general_dependencies.sh as described in step 1 of https://github.com/macarthur-lab/seqr/blob/master/deploy/LOCAL_INSTALL.md"
    exit 1
fi

if [ -z "$(which python3)" ]; then
    echo
    echo "'python3' command not found. Please install python."
    echo
    exit 1
fi


echo "===== Install hail and other python3 dependencies ===="
set -x

wget -nv https://bootstrap.pypa.io/get-pip.py -O get-pip.py
sudo python3 get-pip.py
sudo python3 -m pip install --upgrade pip setuptools
sudo python3 -m pip install --upgrade -r ${SEQR_DIR}/hail_elasticsearch_pipelines/luigi_pipeline/requirements.txt

# set SPARK_HOME to the spark version installed as part of the hail install
unset SPARK_HOME
export SPARK_HOME=$(python3 - <<EOF
from pyspark.find_spark_home import _find_spark_home
print(_find_spark_home())
EOF
)

if [ -z "$SPARK_HOME"  ]; then
    echo "ERROR: Something went wrong while installing hail/pyspark. Make sure \"python3 -m pip install --upgrade hail\" ran successfully."
    exit 1
fi

echo 'export SPARK_HOME='${SPARK_HOME} >> ~/.bashrc

set +x
echo
echo "==== Install data loading pipeline ===="
echo
set -x

# fix http://discuss.hail.is/t/importerror-cannot-import-name-getargspec/468
sudo $(which pip) install --ignore-installed decorator==4.2.1

# install jupyter
sudo $(which pip) install --upgrade pip jupyter

# Download and install VEP GRCh38 - steps based on gs://hail-common/vep/vep/vep95-loftee-1.0-GRCh38-init-docker.sh
export ASSEMBLY=GRCh38  # For GRCh37, see gs://hail-common/vep/vep/vep85-loftee-1.0-GRCh37-init-docker.sh
export VEP_DOCKER_IMAGE=konradjk/vep95_loftee:0.2

sudo mkdir -p /vep_data/loftee_data
sudo mkdir -p /vep_data/homo_sapiens


if [ -z "$PLATFORM" ]; then
    set +x
    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1

elif [ $PLATFORM = "macos" ]; then

    echo "Steps not yet implemented for $PLATFORM"
    exit 1

elif [ $PLATFORM = "centos" ]; then

    sudo yum update
    sudo yum install -y yum-utils device-mapper-persistent-data lvm2

    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo yum install -y docker-ce

elif [ $PLATFORM = "ubuntu" ]; then

    # Install docker
    sudo apt-get update
    sudo apt-get -y install \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg2 \
        software-properties-common \
        tabix
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
    sudo apt-get update
    sudo apt-get install -y --allow-unauthenticated docker-ce

else
    set +x
    echo "Unexpected operating system: $PLATFORM"
    exit 1
fi;

# Get VEP cache and LOFTEE data
gsutil cp gs://hail-common/vep/vep/vep85-loftee-gcloud.json /vep_data/vep85-gcloud.json
gsutil -m cp -r gs://hail-common/vep/vep/loftee-beta/${ASSEMBLY}/* /vep_data/ &
gsutil -m cp -r gs://hail-common/vep/vep/Plugins /vep_data &
gsutil -m cp -r gs://hail-common/vep/vep/homo_sapiens/95_${ASSEMBLY} /vep_data/homo_sapiens/ &
docker pull ${VEP_DOCKER_IMAGE} &
wait

cat > ./vep.c <<EOF
#include <unistd.h>
#include <stdio.h>

int
main(int argc, char *const argv[]) {
  if (setuid(geteuid()))
    perror( "setuid" );

  execv("/vep.sh", argv);
  return 0;
}
EOF

sudo gcc -Wall -Werror -O2 ./vep.c -o /vep
sudo chmod u+s /vep

cat > ./vep.sh <<EOF
#!/bin/bash

docker run -i -v /vep_data/:/opt/vep/.vep/:ro ${VEP_DOCKER_IMAGE} \
  /opt/vep/src/ensembl-vep/vep "\$@"
EOF
chmod +x ./vep.sh

sudo mv ./vep.sh /

set +x

echo Done
