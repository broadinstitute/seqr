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
