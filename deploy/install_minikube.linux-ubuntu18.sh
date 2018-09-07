#!/usr/bin/env bash

export SEQR_BRANCH=master

echo ==== Download deployment scripts =====
set -x

curl -Lo seqr.zip https://github.com/macarthur-lab/seqr/archive/${SEQR_BRANCH}.zip
sudo apt install -y unzip python-dev
unzip -o -d . seqr.zip
rm seqr.zip

set +x
echo ==== Install python dependencies =====
set -x

cd seqr-${SEQR_BRANCH}/

curl -Lo virtualenv-16.0.0.tar.gz https://pypi.python.org/packages/source/v/virtualenv/virtualenv-16.0.0.tar.gz
tar xzf virtualenv-16.0.0.tar.gz
python virtualenv-16.0.0/virtualenv.py --python=python2.7 venv
source venv/bin/activate

pip install -r deploy/deploy-requirements.txt

# source venv on startup
# echo "cd $(pwd); source venv/bin/activate" >> $HOME/.bashrc  # Took this out as it was really annoying! Prefer to cd and start the venv only when I want to run seqr, not every time I use the terminal.

set +x
echo ==== Install and start docker service =====
set -x

sudo apt-get remove docker docker-engine docker.io  # Remove old versions

sudo sysctl net.ipv4.ip_forward=1   # fix for https://stackoverflow.com/questions/41453263/docker-networking-disabled-warning-ipv4-forwarding-is-disabled-networking-wil
sudo sysctl net.bridge.bridge-nf-call-iptables=1
sudo sysctl -p

sudo apt-get update
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo apt-get update
sudo apt-get install -y docker-ce

sudo usermod -a -G docker $USER

sudo systemctl enable docker.service
sudo systemctl start docker.service

set +x
echo ==== Install kubectl =====
## command from https://kubernetes.io/docs/tasks/tools/install-kubectl/
curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod +x kubectl && sudo cp kubectl /usr/bin/ && rm kubectl

echo ==== Install and start minikube =====
set -x

sudo apt-get install socat  # needed for port forwarding when --vm-driver=none (see https://github.com/kubernetes/minikube/issues/2575)

## command from https://github.com/kubernetes/minikube/releases
curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && chmod +x minikube && sudo cp minikube /usr/local/bin/ && rm minikube

sudo rm -rf /etc/kubernetes/  # clean up any previously installed instance

export MINIKUBE_HOME=$HOME
export CHANGE_MINIKUBE_NONE_USER=true
mkdir -p $HOME/.kube
touch $HOME/.kube/config

export KUBECONFIG=$HOME/.kube/config

sudo -E minikube start --vm-driver=none --apiserver-ips 127.0.0.1 --apiserver-name localhost  # fixes network for --vm-driver=none: https://github.com/kubernetes/minikube/issues/2575

sudo chown -R $USER $HOME/.kube
sudo chgrp -R $USER $HOME/.kube
sudo chown -R $USER $HOME/.minikube
sudo chgrp -R $USER $HOME/.minikube

set +x
echo ==== Wait for minikube to start =====

for i in {1..150}; do    # timeout for 5 minutes
   kubectl get po &> /dev/null
   if [ $? -ne 1 ]; then
      break
  fi
  echo 'Waiting for minikube to start...'
  sleep 2
done

minikube status

echo ==== Install java 1.8 =====
set -x

sudo apt update
sudo apt install openjdk-11-jdk

set +x
echo ==== Adjust system settings for elasticsearch =====
set -x

echo '
vm.max_map_count=262144
' | sudo tee -a /etc/sysctl.conf

sudo sysctl -w vm.max_map_count=262144   # avoid elasticsearch error: "max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]"

echo '
* hard	 nofile	65536
* soft	 nofile	65536
elasticsearch  nofile  65536
' | sudo tee -a /etc/security/limits.conf  # avoid elasticsearch error: "max file descriptors [4096] for elasticsearch process is too low, increase to at least [65536]"

# apply limit to current session
sudo prlimit --pid $$ --nofile=65536

set +x
echo ==== Install and start elasticsearch =====
set -x

cd ..

ELASTICSEARCH_VERSION=elasticsearch-6.4.0

curl -L http://artifacts.elastic.co/downloads/elasticsearch/${ELASTICSEARCH_VERSION}.tar.gz -o ${ELASTICSEARCH_VERSION}.tar.gz
tar xzf ${ELASTICSEARCH_VERSION}.tar.gz

echo "ES_JAVA_OPTS='-Xms5000m -Xmx5000m' ./${ELASTICSEARCH_VERSION}/bin/elasticsearch -E network.host=0.0.0.0" | tee start_elasticsearch.sh
chmod 777 ./start_elasticsearch.sh
set +x
./start_elasticsearch.sh
