#!/usr/bin/env bash

export SEQR_BRANCH=more_local_install_updates

echo ==== Download seqr =====

curl -Lo seqr.zip https://github.com/macarthur-lab/seqr/archive/${SEQR_BRANCH}.zip
sudo yum install -y unzip
unzip -o -d seqr seqr.zip

echo ==== Install seqr depencies =====

curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python get-pip.py

sudo pip install -r seqr/*/deploy/dev-requirements.txt


echo ==== Install and start docker service =====

sudo sysctl net.ipv4.ip_forward=1   # fix for https://stackoverflow.com/questions/41453263/docker-networking-disabled-warning-ipv4-forwarding-is-disabled-networking-wil
sudo sysctl net.bridge.bridge-nf-call-iptables=1
#sudo systemctl restart network
sudo sysctl -p

sudo yum install -y yum-utils   device-mapper-persistent-data   lvm2
sudo yum-config-manager     --add-repo     https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce
sudo usermod -a -G docker $USER
sudo systemctl enable docker.service
sudo systemctl start docker.service

echo ==== Install kubectl =====
## command from https://kubernetes.io/docs/tasks/tools/install-kubectl/
curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod +x kubectl && sudo cp kubectl /usr/bin/ && rm kubectl

echo ==== Install and start minikube =====
## command from https://github.com/kubernetes/minikube/releases
curl -Lo minikube https://storage.googleapis.com/minikube/releases/v0.28.2/minikube-linux-amd64 && chmod +x minikube && sudo mv minikube /usr/bin/

sudo rm -rf /etc/kubernetes/  # clean up any previously installed instance

export MINIKUBE_HOME=$HOME
export CHANGE_MINIKUBE_NONE_USER=true
mkdir -p $HOME/.kube
touch $HOME/.kube/config

export KUBECONFIG=$HOME/.kube/config

sudo minikube stop
sudo minikube delete

sudo -E minikube start --vm-driver=none

sudo chown -R $USER $HOME/.kube
sudo chgrp -R $USER $HOME/.kube
sudo chown -R $USER $HOME/.minikube
sudo chgrp -R $USER $HOME/.minikube

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


echo ==== Install and start elasticsearch =====

ELASTICSEARCH_VERSION=elasticsearch-6.4.0
sudo yum install -y java-1.8.0-openjdk.x86_64

sudo sysctl -w vm.max_map_count=262144   # avoid elasticsearch error: "max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]"

echo '
* hard	 nofile	65536
* soft	 nofile	65536
' | sudo tee -a /etc/security/limits.conf  # avoid elasticsearch error: "max file descriptors [4096] for elasticsearch process is too low, increase to at least [65536]"

curl -L http://artifacts.elastic.co/downloads/elasticsearch/${ELASTICSEARCH_VERSION}.tar.gz -o ${ELASTICSEARCH_VERSION}.tar.gz
tar xzf ${ELASTICSEARCH_VERSION}.tar.gz

ES_JAVA_OPTS="-Xms3900m -Xmx3900m" ./${ELASTICSEARCH_VERSION}/bin/elasticsearch -E network.host=0.0.0.0
