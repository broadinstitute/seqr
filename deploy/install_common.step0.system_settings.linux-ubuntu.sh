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

wget -N https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-219.0.1-linux-x86_64.tar.gz
tar xzf google-cloud-sdk-219.0.1-linux-x86_64.tar.gz
./google-cloud-sdk/install.sh --quiet


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

