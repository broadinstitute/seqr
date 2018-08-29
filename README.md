
seqr 
====
[![Build Status](https://travis-ci.org/macarthur-lab/seqr.svg?branch=master)](https://travis-ci.org/macarthur-lab/seqr)

seqr is a web-based analysis tool for rare disease genomics.

This repository contains the code that underlies the [Broad seqr instance](http://seqr.broadinstitute.org) as well as other seqr deployments.

## Overview

seqr consists of the following components:
- seqr - the main client-server application - javascript + react.js on the client-side, python + django on the server-side.
- postgres - SQL database used by seqr and phenotips to store project metadata and user-generated content such as variant notes, etc.
- phenotips - 3rd-party web-based tool for entering structured phenotype information.
- matchbox - a service that encapsulates communication with the Match Maker Exchange.
- nginx - http server used as the main gateway between seqr and the internet.
- pipeline-runner - container for running hail pipelines to annotate and load new datasets. 
- redis - in-memory cache used to speed up request handling.
- elasticsearch - NoSQL database used to store variant callsets.
- kibana - (optional) dashboard and visual interface for elasticsearch.
- mongo - legacy NoSQL database originally used for variant callsets and still used now to store some reference data and logs.


## Install

To install seqr components, we rely on Docker images and Kubernetes. 
Users that are very familiar with these components may opt to install them directly on their host system 
(and we also use this approach for local development). In most cases though, we recommend the added complexity 
of the docker/kubernetes approach because:  1) deployment is automated and avoids manual steps as much as possible. 
This makes it more reproducable and allows more confident experimentation with hardware and cluster configurations. 
Also the [Dockerfiles](https://github.com/macarthur-lab/seqr/tree/master/deploy/docker) serve as both code and documentation for how to install components. 2) as seqr evolves, it's easier to roll out new components or move around existing components if they outgrow existing hardware. 3) the components are isolated from operating system and environment differences across different on-prem and cloud infrastructures.


#### Step 1: Create kubernetes cluster and elasticsearch instance  

Here we will create a kubernetes cluster that will host seqr components, and stand up a separate elasticsearch database outside kubernetes. We use this configuration because, although it's reasonable to deploy elasticsearch on docker/kubernetes, this can complicate some key dev-ops steps like snapshots, loading data using spark, and increasing disk space when needed. 

The instructions below for setting up kubernetes on MacOS and Linux (specifically CentOS7) use [MiniKube](https://kubernetes.io/docs/setup/minikube/) 
to create a self-contained kubernetes cluster on a single machine. There are also instructions for Google Cloud Container Engine (GKE). Many other cloud providers besides Google also have native support for Kubernetes, and other tools besides MiniKube are under development for creating on-prem kubernetes clusters. A list of these other options is here: https://kubernetes.io/docs/setup/pick-right-solution/).

Ok, with that overview out of the way, let's install some components.

##### Local deployment - using MiniKube - MacOS laptop

Prereqs: [homebrew](http://brew.sh/) package manager, python2.7, `sudo` root access 

The following command downloads seqr deployment scripts and then, using `brew` where possible, installs  
- python dependencies
- hypervisor
- kubectl 
- minikube
- java1.8
- elasticsearch

Run this command in the directory you want to contain the elasticsearch installation (as well as seqr installation scripts)  
```
curl -L 'http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/install_minikube.macos.sh' -o install_minikube.macos.sh && chmod 777 install_minikube.macos.sh  && source install_minikube.macos.sh
```


##### Local deployment - using MiniKube - CentOS / RedHat server

Prereqs: python2.7, `sudo` root access

The following command downloads seqr deployment scripts and then, using `yum` where possible, installs 
- python dependencies
- docker 
- kubectl 
- minikube
- java1.8
- elasticsearch

Run it in the directory you want to contain the elasticsearch installation (as well as seqr scripts)
```
curl -L 'http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/install_minikube.linux-centos7.sh' -o install_minikube.linux-centos7.sh && chmod 777 install_minikube.linux-centos7.sh  && source install_minikube.linux-centos7.sh
```

##### Cloud deployment - Google Container Engine (GKE) 

Download or clone a local copy of this github repository. 

Install these tools:
- [docker](https://store.docker.com/search?type=edition&offering=community) 
- [gcloud tools](https://cloud.google.com/sdk/install)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)

Make sure you have a google account that's configured to use Google Compute Engine (GCE) and 
has everything in place for creating a private Kubernetes Engine (GKE) cluster (see details here: 
https://cloud.google.com/kubernetes-engine/docs/how-to/creating-a-cluster)

Now, running these commands in your local shell will point gcloud and kubectl tools to your GCE project:
```
export KUBECONFIG=~/.kube/config   # used by kubectl

gcloud config set core/project <your gcloud project name>
gcloud config set compute/zone <your compute zone>
``` 

Next, in order to setup an elasticsearch instance, create linux VM(s) in your google project.
The VM(s) should be on the default private network which will later also contain the GKE cluster nodes.   
Once the VM(s) are ready, install and launch elasticsearch on them - using similar commands as those at the bottom of [install_minikube.linux-centos7.sh](https://github.com/macarthur-lab/seqr/blob/master/deploy/install_minikube.linux-centos7.sh). 


#### Step 2: Adjust seqr deployment settings

The following files contain settings that you may want to adjust before proceeding to step 3:

* `deploy/kubernetes/*-settings.yaml` - you will want to edit the specific to your deployment target (for example `minikube-settings.yaml`).  
* `deploy/secrets/shared/*` - directories that contain keys, passwords and other sensitive info that shouldn't be shared publicly.
     You will want to edit:
  * *gcloud/service-account-key.json* - allows gcloud and kubectl to access google cloud resources in your project from within pods. We provide a placeholder key which can access public resources.
  * *nginx/tls.cert* and *nginx/tls.key* - ssh keys that allow https access and avoid web browser "insecure website" warnings. https connections are critical for encrypting seqr logins, so you will want to order your own keys before making your seqr instance visible over the internet.    
  * *seqr/postmark_server_token* - seqr uses this to send outgoing emails via postmark.com mail service
  * *seqr/omim_key* - api key for downloading the latest omim files. We provide a placeholder key, but you'll want to use your own.
  * *matchbox/nodes.json* - contains the list of all nodes that matchbox can connect to on the MME network, along with the authentication token for each node.  


#### Step 3: Deploy seqr components

The `./servctl` wrapper script provides a convenient way to run common operations like initializing the kubernetes cluster, deploying components, checking status, looking at logs, etc. It works by running `gcloud`, `kubectl`, `docker` and other command line tools.

For step 3, `./servctl` has a "deploy-all" subcommand that runs the sequence of commands to deploy all components, load reference data, and create an example seqr project. 
 
```
./servctl deploy-all {target}    # here {target} is one of `minikube`, `gcloud-dev` or `gcloud-prod`  
``` 

It will takes many hours to run.


## Update / Migrate an older xBrowse Instance

[Update/Migration Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/MIGRATE.md) 


## Deploy and manage seqr components

   
The `./servctl` wrapper script provides sub-commands for deploying and interacting with seqr components running on kubernetes. 
 
 Run `./servctl -h` to see all available subcommands. The most commonly used ones are:

    *** {component-name} is one of:  init-cluster, secrets, nginx, phenotips, postgres, seqr, etc. 
    *** {deployment-target}  is one of:  minikube, gcloud-dev, or gcloud-prod 

      deploy-all  {deployment-target}                       # end-to-end deployment - deploys all seqr components 
      deploy {component-name} {deployment-target}           # deploy some specific component(s)
      
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
      
    
## Data loading pipelines

seqr uses [hail](http://hail.is)-based pipelines to run VEP and add in other reference data before loading them into elasticsearch. 
These pipelines can be run locally on a single machine or on-prem spark cluster, or on a cloud-based spark cluster such as Google Dataproc.
We are working on integrating these pipelines so that they are launched and managed by seqr. 
For now, they must be run manually, as shown in the examples below. The code for these pipelines is in [Data annotation and loading pipelines](https://github.com/macarthur-lab/hail-elasticsearch-pipelines) 
and is automatically installed in the `pipeline-runner` component which is deployed as part of standard seqr deployment.  

Example using minikube:
```
# after you've deployed seqr to minikube, open a shell within the pipeline-runner pod
./servctl shell pipeline-runner minikube
 
export SEQR_PROJECT_GUID=R003_seqr_project3  # guid of existing seqr project
export VCF_PATH=/data/my-exome-dataset.vcf.gz   # local or google cloud bucket VCF path 

/hail-elasticsearch-pipelines/run_hail_locally.sh \
        --driver-memory 5G \
        --executor-memory 5G \
        hail_scripts/v01/load_dataset_to_es.py \
            --genome-version 37 \
            --project-guid $SEQR_PROJECT_GUID \
            --sample-type WES \
            --dataset-type VARIANTS \
            --exclude-hgmd \
            --vep-block-size 10 \
            --es-block-size 10 \
            --num-shards 1 \
            --max-samples-per-index 99 \
            $VCF_PATH

# after the pipeline completes successfully, you can link the new elasticsearch index to the seqr project by using the 'Edit Datasets' dialog on the project page.
```

Example with seqr deployed to google cloud GKE, and using Google Dataproc to run the pipeline:
``` 
# these commands should be run locally on your laptop  
git clone git@github.com:macarthur-lab/hail-elasticsearch-pipelines.git
  
cd hail-elasticsearch-pipelines 
export IP=56.4.0.3   # IP address of elasticsearch instance running on google cloud on the project-default network so that it's visible to dataproc nodes, but not to the public internet. 
export SEQR_PROJECT_GUID=R003_seqr_project3  # guid of existing seqr project
export GS_VCF_PATH=gs://seqr-datasets/GRCh38/my-new-dataset.vcf.gz   # VCF path on cloud storage
  
# this will create a new dataproc cluster and submit the pipeline to it 
python gcloud_dataproc/load_GRCh38_dataset.py --host $IP --project-guid SEQR_PROJECT_GUID --sample-type WGS --dataset-type VARIANTS $GS_VCF_PATH --es-block-size 50  
  
# after the pipeline completes successfully, you can link the new elasticsearch index to the seqr project by using the 'Edit Datasets' dialog on the project page. 
```


   
## Kubernetes Resources


- Official Kuberentes User Guide:  https://kubernetes.io/docs/user-guide/
- 15 Kubernetes Features in 15 Minutes: https://www.youtube.com/watch?v=o85VR90RGNQ
- Kubernetes: Up and Running: https://www.safaribooksonline.com/library/view/kubernetes-up-and/9781491935668/
- The Children's Illustrated Guide to Kubernetes: https://deis.com/blog/2016/kubernetes-illustrated-guide/
