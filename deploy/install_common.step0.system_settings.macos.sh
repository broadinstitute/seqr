#!/usr/bin/env bash


echo ===== Install general depencies =====
set -x

brew update
brew install gcc
brew install unzip wget bzip2
brew install git gcc make patch


echo ===== Install java 1.8 =====
brew tap caskroom/versions
brew cask install java8       # needed to run elasticsearch


wget https://bootstrap.pypa.io/get-pip.py
sudo python get-pip.py
sudo pip install --upgrade pip setuptools


set +x
echo ==== Install gcloud sdk =====
set -x


# TODO

set +x
echo ==== Clone the seqr repo =====
set -x


if [ -z "$SEQR_DIR" ]; then

    export SEQR_BRANCH=master

    git clone https://github.com/macarthur-lab/seqr.git
    cd seqr/
    git checkout $SEQR_BRANCH

    export SEQR_DIR=$(pwd)
    echo '
    # ---- seqr install -----
    export SEQR_DIR='${SEQR_DIR}'
    ' >> ~/.bash_profile

    cd ..
fi
