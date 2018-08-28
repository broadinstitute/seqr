
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


## Installation

To install the above components, we rely on Docker images and Kubernetes. 
Users that are very familiar with these components may opt to install them directly on their host system 
(and we also use this approach for local development). In most cases though, we recommend the added complexity 
of the docker/kubernetes approach because:  1) deployment is automated and avoids manual steps as much as possible. 
This makes it more reproducable and allows more confident experimentation with hardware and cluster configurations. 
Also the Docker files serve as both code and documentation for how to install components. 2) as seqr evolves, it's easier to roll out new components or re-arrange existing components if they outgrow existing hardware. 3) the components are isolated from operating system and environment differences across different on-prem and cloud infrastructures.


#### Step 1: Create kubernetes cluster and elasticsearch instance  

Here we will create a kubernetes cluster that will host all seqr components except elasticsearch, 
and also stand up an elasticsearch database outside kubernetes. 
We use this configuration because, although it's reasonable to deploy elasticsearch to docker/kubernetes, this can complicate some key dev-ops steps 
like backup/snapshotting, loading data from spark, and increasing disk space when needed. 

The instructions below for setting up kubernetes on MacOS and Linux (specifically CentOS7) use [MiniKube](https://kubernetes.io/docs/setup/minikube/) 
to create a self-contained kubernetes cluster on a single machine. There are also instructions for Google Cloud Container Engine (GKE). 
Many other cloud providers also have native support for Kubernetes, and other tools besides MiniKube are under development for 
creating on-prem kubernetes clusters. A list of these other options is here: https://kubernetes.io/docs/setup/pick-right-solution/).
 

##### Local deployment - using MiniKube - MacOS laptop

TODO

##### Local deployment - using MiniKube - CentOS / RedHat server

Requirements: python2.7, root access using `sudo` 
```
curl -L 'http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/install_minikube.linux-centos.sh' -o install_minikube.linux-centos.sh && chmod 777 install_minikube.linux-centos.sh  && source install_minikube.linux-centos.sh
```

##### Cloud deployment - Google Container Engine (GKE) 

TODO
  

#### Step 2: Adjust seqr options


#### Step 3: Install elasticsearch


#### Step 4: Install all other components

The ./servctl wrapper has a "deploy-all" sub-command that runs a sequence of docker and kubectl commands to build docker images for all components and deploy 
them to the Kuberenes cluster. At the end it also loads reference data and an example dataset. You can expect it to take many hours. 
```
./servctl deploy-all {target}    # here {target} is one of `minikube`, `gcloud-dev` or `gcloud-prod`  
``` 



[Kubernetes-based Installation Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/kubernetes) - The [Kubernetes](https://kubernetes.io/)-based installation allows for fully scripted deployment of all seqr components. It supports local installation on any operating system using a virtualized environment ([minikube](https://github.com/kubernetes/minikube)) as well as cloud deployment on Google, AWS, and other clouds.  

[Data pre-processing and loading pipelines](https://github.com/macarthur-lab/hail-elasticsearch-pipelines) - [hail](http://hail.is) pipelines for pre-processing and loading datasets into an elasticsearch datastore.  



## Update / Migration of older xBrowse Instance

[Update/Migration Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/MIGRATE.md) - instructions for updating an existing xBrowse instance 

  
**Please Note:** seqr is still under active development, and undergoing refactoring. We suggest you contact us if you want to build on this repo.
