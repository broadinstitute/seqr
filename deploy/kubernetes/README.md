This README describes how to deploy a local or a cloud-based instance of seqr using [Kubernetes](https://kubernetes.io/).

Overview
--------

seqr consists of the following components or micro-services:
- seqr - the main client-server application - javascript + react.js on the client-side, python + django on the server-side.
- postgres - SQL database used by seqr and phenotips to store metadata and small reference datasets (eg. OMIM, clinvar).
- phenotips - 3rd-party web-based tool for entering structured phenotype information.
- mongo - NoSQL database used to store large variant datasets and reference data. This is being phased out in favor of elasticsearch.
- matchbox - a service that encapsulates communication with the Match Maker Exchange
- nginx - http server used as the main gateway between seqr and the internet.
- elasticsearch - NoSQL database that's replacing mongo as the database storing reference data and variant callsets in seqr.
- kibana - (optional) user-friendly visual interface to elasticsearch.



Prerequisites
-------------

Make sure `python2.7` is installed

Clone this github repo to a subdirectory of your `HOME` directory (for example: ~/code/seqr), and install python dependencies:  

       cd ~/code
       git clone https://github.com/macarthur-lab/seqr.git
       
       cd seqr
       pip install -r requirements.txt




Create Kubernetes Cluster
-------------------------

**Local Instance on MacOSX or other operating system**

The local installation relies on [minikube](https://github.com/kubernetes/minikube) - the officially-supported way to install a local Kubernetes cluster.

1. [Install Minicube](https://kubernetes.io/docs/tasks/tools/install-minikube/)
  
     On MacOS you can do this by running:
     ```
     curl -Lo minikube https://storage.googleapis.com/minikube/releases/v0.23.0/minikube-darwin-amd64 && chmod +x minikube && sudo mv minikube /usr/local/bin/
     
     brew install docker-machine-driver-xhyve
     sudo chown root:wheel /usr/local/opt/docker-machine-driver-xhyve/bin/docker-machine-driver-xhyve
     sudo chmod u+s /usr/local/opt/docker-machine-driver-xhyve/bin/docker-machine-driver-xhyve
     ```

2. [Install kubectl](https://kubernetes.io/docs/tasks/kubectl/install/) 

3. Start the local minikube kubernetes cluster:
    
    ```
    minikube start --disk-size=50g --memory 8000 --cpus 8 --vm-driver=xhyve
    ```
 

**Cloud-based Instance**

Most major cloud providers (including Google, AWS, Azure, and others) now have robust Kubernetes support and provide user-friendly ways to create Kubernetes clusters and then deploy, manage, and scale Kubernetes-based components. The following steps are necessary before `./servctl` can be used to deploy to a Google Container Engine cluster:

1. Install Docker  ([MacOSX installer](https://getcarina.com/docs/tutorials/docker-install-mac/) ) 
   
   It will be used to build docker images before pushing them to your private repo on Google Container Engine.

2. [Install kubectl](https://kubernetes.io/docs/tasks/kubectl/install/)

3. Create a Kuberentes cluster using cloud provider-specific instructions (eg. [Google](https://cloud.google.com/kubernetes-engine/docs/quickstart), [AWS](https://kubernetes.io/docs/getting-started-guides/aws/), [Azure](https://kubernetes.io/docs/getting-started-guides/azure/), [others](https://kubernetes.io/partners/))


Configuration
-------------

The seqr installation process described below should produce a working instance with default settings.  
However, for best results, you may want to first adjust the following parameters.  
*NOTE:* File paths below are relative to `~/code/seqr/deploy/kubernetes`  

`secrets/*/*.*` - these directories contain private or sensitive settings for each seqr component - such as passwords, tockens, and SSL keys. Changes to these files should not be committed to github. Instead they are securely handed to kubernetes and injected into relevant components during deployment using Kubernetes secrets-related features.    
 
 Particularly you want to configure the following secrets files:   
    
     secrets/*/nginx/tls.* - SSL certificates to enable HTTPS for the externally-visible production-grade nginx server. In the dev. instance, self-signed certificates can be used (see https://github.com/kubernetes/ingress/blob/master/examples/PREREQUISITES.md#tls-certificates for example commands for creating self-signed certs). 
     secrets/*/postgres/postgres.* - the postgres database will be configured to require this username and password. The database isn't visible outside the Kubernetes internal network, so these are not the primary level of security.
     secrets/*/seqr/omim_key - this key can be obtained by filling out the form at https://omim.org/api 
    
    
    
`settings/*-settings.yaml` - these files contain non-private settings for each type of deployment, and can be customized for local deployments (particularly `gcloud-settings.yaml`).  


Deploy and Manage Seqr
----------------------

To deploy all seqr components to your Kubernetes environment, 

    cd ~/code/seqr
    ./servctl deploy-all-and-load {deployment-target}   # deployment-target can be 'minikube', 'gcloud-dev', or 'gcloud-prod'
   


The `./servctl` script provides subcommands for deploying and interacting with seqr components, and
 performing other common development and troubleshooting operations. 
 
 Run `./servctl -h` to see all available subcommands. The most commonly used subcommands are:

      deploy-all-and-load  {deployment-target}              # end-to-end deployment - deploys all seqr components and loads reference data + an example project
      deploy {component-name} {deployment-target}           # deploy one or more components
      
      status {deployment-target}                            # print status of all kubernetes and docker subsystems
      set-env {deployment-target}                           # deploy one or more components
      dashboard {deployment-target}                         # open the kubernetes dasbhoard in a browser
      
      shell {component-name} {deployment-target}            # open a bash shell inside one of the component containers
      logs {component-name} {deployment-target}             # show logs for one or more components
      troubleshoot {component-name} {deployment-target}     # print more detailed info that may be useful for discovering why a component is failing during pod initialization
      connect-to {component-name} {deployment-target}       # shows logs, and also sets up a proxy so that the server running inside this component can be accessed from http://localhost:<port> 
      
      copy-to {component-name} {deployment-target} {local-path}           # copy a local file to one of the pods
      copy-from {component-name} {deployment-target} {path} {local-path}  # copy a file from one of the pods to a local directory
      
      delete {component-name} {deployment-target}           # undeploys the component
      
    *** {component-name}  should be one of these:  init-cluster, secrets, nginx, phenotips, postgres, seqr, etc. 
    *** {deployment-target}  should be one of these:  minikube, gcloud-dev, or gcloud-prod 


Kubernetes Resources
--------------------

- Official Kuberentes User Guide:  https://kubernetes.io/docs/user-guide/
- 15 Kubernetes Features in 15 Minutes: https://www.youtube.com/watch?v=o85VR90RGNQ
- Kubernetes: Up and Running: https://www.safaribooksonline.com/library/view/kubernetes-up-and/9781491935668/
- The Children's Illustrated Guide to Kubernetes: https://deis.com/blog/2016/kubernetes-illustrated-guide/

