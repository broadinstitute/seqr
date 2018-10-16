#!/usr/bin/env bash

# get --vm-driver value from VM_DRIVER env var. if defined, or use "none" by default
VM_DRIVER="${VM_DRIVER:-none}"

set +x
echo ==== Install and start docker service =====
set -x

sudo apt-get remove -y docker docker-engine docker.io  # Remove old versions

sudo sysctl net.ipv4.ip_forward=1   # fix for https://stackoverflow.com/questions/41453263/docker-networking-disabled-warning-ipv4-forwarding-is-disabled-networking-wil
sudo sysctl net.bridge.bridge-nf-call-iptables=1
sudo sysctl -p

sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

sudo apt-get update
sudo apt-get install -y docker-ce

sudo systemctl enable docker.service
sudo systemctl start docker.service

if groups $USER | grep &>/dev/null '\bdocker\b'; then
    echo User already in docker group.
else
    sudo usermod -a -G docker $USER

    needs_reboot=1
fi

set +x
echo ==== Install kubectl and minikube =====
set -x

# crictl is required for starting minikube with --kubernetes-version=v1.11
CRICTL_VERSION="v1.11.1"
wget -N https://github.com/kubernetes-sigs/cri-tools/releases/download/$CRICTL_VERSION/crictl-$CRICTL_VERSION-linux-amd64.tar.gz
sudo tar zxvf crictl-$CRICTL_VERSION-linux-amd64.tar.gz -C /usr/bin
rm -f crictl-$CRICTL_VERSION-linux-amd64.tar.gz

## command from https://kubernetes.io/docs/tasks/tools/install-kubectl/
curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && chmod +x kubectl && sudo cp kubectl /usr/bin/ && rm kubectl

## command from https://github.com/kubernetes/minikube/releases
curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && chmod +x minikube && sudo cp minikube /usr/bin/ && rm minikube

sudo rm -rf /etc/kubernetes/  # clean up any previously installed instance
sudo apt-get install -y socat  # needed for port forwarding when --vm-driver=none (see https://github.com/kubernetes/minikube/issues/2575)

mkdir -p $HOME/.kube
touch $HOME/.kube/config

# There are DNS issues like https://github.com/kubernetes/minikube/issues/2027 on Unbuntu (and probably other systems)
# when running with --vm-driver=none which result in DNS lookups not working inside pods for external web addresses.
# This work-around corrects this by setting the upstream DNS server to google's server (8.8.8.8) which is known to work.
echo 'kind: ConfigMap
apiVersion: v1
data:
  Corefile: |
    .:53 {
        errors
        health
        kubernetes cluster.local in-addr.arpa ip6.arpa {
           pods insecure
           upstream
           fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        proxy . 8.8.8.8
        cache 30
        reload
    }
metadata:
  creationTimestamp: 2018-09-09T18:24:22Z
  name: coredns
  namespace: kube-system
  resourceVersion: "198"
  selfLink: /api/v1/namespaces/kube-system/configmaps/coredns' > coredns-config.yaml


echo 'sudo minikube stop' > stop_minikube.sh
chmod 777 stop_minikube.sh

echo '#!/usr/bin/env bash

export CHANGE_MINIKUBE_NONE_USER=true
export MINIKUBE_HOME=$HOME
export KUBECONFIG=$HOME/.kube/config

NUM_CPUS=$(python -c "import multiprocessing; print(multiprocessing.cpu_count())")
DISK_SIZE=50g

set -x
sudo rm -rf /etc/kubernetes/  # clean up any previously installed instance
echo Y | sudo minikube stop
echo Y | sudo minikube delete

sudo -E minikube start --kubernetes-version=v1.11.3 --memory=5000 --vm-driver='${VM_DRIVER}' --cpus=${NUM_CPUS} --disk-size=${DISK_SIZE}

set +x

sudo chown -R $USER $HOME/.kube
sudo chgrp -R $USER $HOME/.kube
sudo chown -R $USER $HOME/.minikube
sudo chgrp -R $USER $HOME/.minikube

sudo minikube addons enable coredns

# make sure all kube-dns components are deleted
sudo minikube addons disable kube-dns
kubectl delete deployment kube-dns -n=kube-system
kubectl delete svc kube-dns -n=kube-system

kubectl delete -f '$(pwd)'/coredns-config.yaml
kubectl create -f '$(pwd)'/coredns-config.yaml

kubectl patch deployment -n=kube-system coredns -p '\''{"spec": {"template": {"spec":{"containers":[{"name":"coredns","resources":{"limits":{"memory":"1Gi"}}}]}}}}'\''

' > start_minikube.sh

chmod 777 start_minikube.sh
./start_minikube.sh
