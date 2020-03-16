#!/usr/bin/env bash

echo ==== Set environment variables =====

if [ -z "$(which python)" ]; then
    echo
    echo "'python' command not found. Please install python."
    echo
    exit 1
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
    cat <(echo 'export PLATFORM='${PLATFORM}) ~/.bashrc > /tmp/bashrc && mv /tmp/bashrc ~/.bashrc

fi


if [ -z "$SEQR_DIR"  ]; then

    export SEQR_DIR=$(pwd)/seqr
    export SEQR_BIN_DIR=${SEQR_DIR}/../bin
    cat <(echo 'export SEQR_DIR='${SEQR_DIR}) ~/.bashrc > /tmp/bashrc && mv /tmp/bashrc ~/.bashrc
    cat <(echo 'export SEQR_BIN_DIR='${SEQR_BIN_DIR}) ~/.bashrc > /tmp/bashrc && mv /tmp/bashrc ~/.bashrc
    cat <(echo 'export PATH='${SEQR_BIN_DIR}':$PATH') ~/.bashrc > /tmp/bashrc && mv /tmp/bashrc ~/.bashrc

fi


set +x
echo ==== Adjust system settings for elasticsearch =====
set -x

# vm.max_map_count needs to be increased on linux for elasticsearch to run. It's not necessary on Mac.
MAX_MAP_COUNT=$(sysctl -b vm.max_map_count)
if [[ -n "$MAX_MAP_COUNT" ]] && (( $MAX_MAP_COUNT < 262144 )); then
    echo '
vm.max_map_count=262144
' | sudo tee -a /etc/sysctl.conf

    sudo sysctl -w vm.max_map_count=262144   # avoid elasticsearch error: "max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]"

    needs_reboot=1
fi

if (( $(ulimit -n) < 65536)); then

    echo '
* hard	 nofile 65536
* soft	 nofile	65536
elasticsearch  nofile  65536
' | sudo tee -a /etc/security/limits.conf  # avoid elasticsearch error: "max file descriptors [4096] for elasticsearch process is too low, increase to at least [65536]"

    if [ $PLATFORM = "ubuntu" ]; then
        echo '
DefaultLimitNOFILE=65536
' | sudo tee -a /etc/systemd/user.conf

        echo '
DefaultLimitNOFILE=65536
' | sudo tee -a /etc/systemd/system.conf

        echo '
session required pam_limits.so
' | sudo tee -a /etc/pam.d/su
    fi

    needs_reboot=1
fi

# apply limit to current session
sudo prlimit --pid $$ --nofile=65536


set +x
echo ==== Install general dependencies =====
set -x

if [ -z "$PLATFORM" ]; then
    set +x
    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1

elif [ $PLATFORM = "macos" ]; then

    brew update
    brew install gcc
    brew install unzip wget bzip2
    brew install git gcc make patch

    brew tap caskroom/versions
    brew cask install java8

elif [ $PLATFORM = "centos" ]; then
    sudo yum install -y unzip wget bzip2
    sudo yum install -y git gcc make patch
    sudo yum install -y java-1.8.0-openjdk.x86_64
    sudo yum install -y python-devel

elif [ $PLATFORM = "ubuntu" ]; then
    sudo apt-get update
    sudo apt-get install -y unzip wget bzip2     # general utilities
    sudo apt-get install -y git gcc make patch   # general devel. deps.
    sudo apt-get install -y openjdk-8-jdk        # java - used by elasticsearch, phenotips, hail, etc.
    sudo apt-get install -y python-dev           # python - used by seqr, etc.
else
    set +x
    echo "Unexpected operating system: $PLATFORM"
    exit 1
fi;

wget -nv https://bootstrap.pypa.io/get-pip.py -O get-pip.py
sudo python get-pip.py
sudo pip install --upgrade pip setuptools

set +x
echo ==== Install gcloud sdk =====
set -x

if [ -z "$PLATFORM" ]; then
    set +x
    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1

elif [ $PLATFORM = "macos" ]; then

    # based on https://cloud.google.com/sdk/docs/quickstart-macos
    wget -N https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-221.0.0-darwin-x86_64.tar.gz
    tar xzf google-cloud-sdk-221.0.0-darwin-x86_64.tar.gz
    rm google-cloud-sdk-221.0.0-darwin-x86_64.tar.gz
    ./google-cloud-sdk/install.sh --quiet

    # make sure crcmod is installed for copying files with gsutil
    sudo easy_install -U pip
    sudo pip install -U crcmod

elif [ $PLATFORM = "centos" ]; then

    sudo tee /etc/yum.repos.d/google-cloud-sdk.repo << EOM
[google-cloud-sdk]
name=Google Cloud SDK
baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg
       https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOM
    sudo yum install -y google-cloud-sdk

    # make sure crcmod is installed for copying files with gsutil
    sudo yum install -y gcc python-devel python-setuptools redhat-rpm-config
    sudo easy_install -U pip
    sudo pip uninstall crcmod
    sudo pip install -U crcmod

elif [ $PLATFORM = "ubuntu" ]; then

    # copied from https://cloud.google.com/sdk/docs/quickstart-debian-ubuntu

    # Create environment variable for correct distribution
    export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)"
    # Add the Cloud SDK distribution URI as a package source
    echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
    # Import the Google Cloud Platform public key
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
    # Update the package list and install the Cloud SDK
    sudo apt-get update && sudo apt-get install -y google-cloud-sdk

    # make sure crcmod is installed for copying files with gsutil
    sudo apt-get install -y gcc python-dev python-setuptools
    sudo easy_install -U pip
    sudo pip uninstall crcmod
    sudo pip install -U crcmod

else
    set +x
    echo "Unexpected operating system: $PLATFORM"
    exit 1
fi;


set +x

echo "==== Clone the seqr repo ====="
set -x

export SEQR_BRANCH=master

git clone --recursive https://github.com/macarthur-lab/seqr.git
cd seqr/
git checkout $SEQR_BRANCH
cd ..

set +x

echo "===== init gsutil ====="

# Add a generic key for accessing public google cloud storage buckets
# Using a top-level /.config directory so that config files (like core-site.xml) can be shared with the Docker container
sudo mkdir -p /.config/
sudo chmod 777 /.config/
cp ${SEQR_DIR}/deploy/secrets/shared/gcloud/* /.config/

if [ -e "/.config/service-account-key.json" ]; then
    # authenticate to google cloud using service account
    gcloud auth activate-service-account --key-file /.config/service-account-key.json
    cp /.config/boto ~/.boto
    sudo mv /etc/boto.cfg /etc/boto.cfg.aside  # /etc/boto.cfg leads to "ImportError: No module named google_compute_engine" on gcloud Ubuntu VMs, so move it out of the way
fi


# check that gsutil works and is able to access gs://hail-common/
GSUTIL_TEST="gsutil ls gs://hail-common/vep"
$GSUTIL_TEST
if [ $? -eq 0 ]; then
    echo gsutil works
else
    echo "$GSUTIL_TEST failed - unable to access public gs://hail-common bucket."
    echo "Try running 'gcloud init'. "
    exit 1
fi

echo "===== init utilities ====="
# install tabix, bgzip, samtools - which may be needed for VEP and the loading pipeline
mkdir -p $SEQR_BIN_DIR
gsutil -m cp gs://hail-common/vep/htslib/* ${SEQR_BIN_DIR}/ \
    && gsutil -m cp gs://hail-common/vep/samtools ${SEQR_BIN_DIR}/ \
    && chmod a+rx  ${SEQR_BIN_DIR}/tabix ${SEQR_BIN_DIR}/bgzip ${SEQR_BIN_DIR}/htsfile ${SEQR_BIN_DIR}/samtools


if [ "$needs_reboot" ] ; then

  echo '
  ==================================================================
  Config changes above will take effect after a reboot.
  ==================================================================
'
    read -p "Reboot now? [y/n] " -n 1 -r
    echo    # (optional) move to a new line
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo "Shutting down..."
        sudo reboot
    else
        echo "Skipping reboot."
    fi
fi
