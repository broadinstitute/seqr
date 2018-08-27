#!/usr/bin/env bash

export GIT_BRANCH=more_local_install_updates

## retrieve seqr zip
curl -Lo seqr.zip https://github.com/macarthur-lab/seqr/archive/${GIT_BRANCH}.zip
sudo yum install -y unzip
unzip -o -d seqr seqr.zip

## install seqr install depencies
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python get-pip.py

sudo pip install -r seqr/*/deploy/dev-requirements.txt


## install docker and start docker service
sudo sysctl net.ipv4.ip_forward=1   # fix for https://stackoverflow.com/questions/41453263/docker-networking-disabled-warning-ipv4-forwarding-is-disabled-networking-wil
sudo systemctl restart network

sudo yum install -y yum-utils   device-mapper-persistent-data   lvm2
sudo yum-config-manager     --add-repo     https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce
sudo usermod -a -G docker $USER
sudo systemctl enable docker.service
sudo systemctl start docker.service

## install kubectl  (see https://kubernetes.io/docs/tasks/tools/install-kubectl/)
curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod +x kubectl && sudo cp kubectl /usr/bin/ && rm kubectl

## install minikube (see https://github.com/kubernetes/minikube/releases)
sudo rm -rf /etc/kubernetes/
curl -Lo minikube https://storage.googleapis.com/minikube/releases/v0.28.2/minikube-linux-amd64 && chmod +x minikube && sudo mv minikube /usr/bin/

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

# this for loop waits until kubectl can access the api server that Minikube has created
for i in {1..150}; do    # timeout for 5 minutes
   kubectl get po &> /dev/null
   if [ $? -ne 1 ]; then
      break
  fi
  echo 'Waiting for minikube to start...'
  sleep 2
done

minikube status
