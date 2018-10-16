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

# based on https://cloud.google.com/sdk/docs/quickstart-macos
wget -N https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-221.0.0-darwin-x86_64.tar.gz
tar xzf google-cloud-sdk-221.0.0-darwin-x86_64.tar.gz
./google-cloud-sdk/install.sh --quiet

set +x