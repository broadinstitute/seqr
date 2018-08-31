#!/usr/bin/env bash

export SEQR_BRANCH=master

echo ==== Download deployment scripts =====

curl -Lo seqr.zip https://github.com/macarthur-lab/seqr/archive/${SEQR_BRANCH}.zip
unzip -o -d seqr seqr.zip


echo ==== Install python dependencies =====

curl -Lo virtualenv-16.0.0.tar.gz https://pypi.python.org/packages/source/v/virtualenv/virtualenv-16.0.0.tar.gz
tar xzf virtualenv-16.0.0.tar.gz
python virtualenv-16.0.0/virtualenv.py --python=python2.7 venv
source venv/bin/activate

pip install -r deploy/deploy-requirements.txtsudo pip install -r seqr/seqr-${SEQR_BRANCH}/deploy/deploy-requirements.txt

echo ==== Install xhyve hypervisor =====
brew update

brew install --HEAD xhyve # from https://github.com/mist64/xhyve


echo ==== Install kubectl =====
brew install kubernetes-cli   # from https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-with-homebrew-on-macos


echo ==== Install minikube =====
brew cask install minikube    # from https://github.com/kubernetes/minikube/releases


echo ==== Install java 1.8 =====

brew tap caskroom/versions
brew cask install java8

echo ==== Install and start elasticsearch =====

ELASTICSEARCH_VERSION=elasticsearch-6.4.0

curl -L http://artifacts.elastic.co/downloads/elasticsearch/${ELASTICSEARCH_VERSION}.tar.gz -o ${ELASTICSEARCH_VERSION}.tar.gz
tar xzf ${ELASTICSEARCH_VERSION}.tar.gz

ES_JAVA_OPTS="-Xms3900m -Xmx3900m" ./${ELASTICSEARCH_VERSION}/bin/elasticsearch -E network.host=0.0.0.0

