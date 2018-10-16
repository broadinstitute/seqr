#!/usr/bin/env bash


if [ -z "$SEQR_DIR" ]; then

    export SEQR_DIR=$(pwd)/seqr

    echo '
    # ---- seqr install -----
    export SEQR_DIR='${SEQR_DIR}'
    ' >> ~/.bashrc
fi


set +x
echo ==== Adjust system settings for elasticsearch =====
set -x

if (( $(sysctl -b vm.max_map_count) < 262144 )); then

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

    needs_reboot=1
fi

# apply limit to current session
sudo prlimit --pid $$ --nofile=65536

set +x
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


set +x
echo ==== Install general dependencies =====
set -x

sudo yum install -y unzip wget bzip2
sudo yum install -y git gcc make patch
sudo yum install -y java-1.8.0-openjdk.x86_64
sudo yum install -y python-devel

wget https://bootstrap.pypa.io/get-pip.py
sudo python get-pip.py
sudo pip install --upgrade pip setuptools

set +x
echo ==== Install gcloud sdk =====
set -x

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

set +x