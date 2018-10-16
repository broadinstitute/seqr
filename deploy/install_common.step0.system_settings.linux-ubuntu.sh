#!/usr/bin/env bash

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
* hard	 nofile	65536
* soft	 nofile	65536
elasticsearch  nofile  65536
' | sudo tee -a /etc/security/limits.conf  # avoid elasticsearch error: "max file descriptors [4096] for elasticsearch process is too low, increase to at least [65536]"

    echo '
DefaultLimitNOFILE=65536
' | sudo tee -a /etc/systemd/user.conf

    echo '
DefaultLimitNOFILE=65536
' | sudo tee -a /etc/systemd/system.conf

    echo '
session required pam_limits.so
' | sudo tee -a /etc/pam.d/su

    needs_reboot=1
fi

# apply limit to current session
sudo prlimit --pid $$ --nofile=65536


set +x
echo ==== Install general dependencies =====
set -x

sudo apt-get update
sudo apt-get install -y unzip wget bzip2     # general utilities
sudo apt-get install -y git gcc make patch   # general devel. deps.
sudo apt-get install -y openjdk-8-jdk        # java - used by elasticsearch, phenotips, hail, etc.
sudo apt-get install -y python-dev           # python - used by seqr, etc.

wget https://bootstrap.pypa.io/get-pip.py
sudo python get-pip.py
sudo pip install --upgrade pip setuptools

set +x
echo ==== Install gcloud sdk =====
set -x

# copied from https://cloud.google.com/sdk/docs/quickstart-debian-ubuntu

# Create environment variable for correct distribution
export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)"
# Add the Cloud SDK distribution URI as a package source
echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# Import the Google Cloud Platform public key
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
# Update the package list and install the Cloud SDK
sudo apt-get update && sudo apt-get install -y google-cloud-sdk

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

