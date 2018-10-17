
seqr
====
[![Build Status](https://travis-ci.org/macarthur-lab/seqr.svg?branch=master)](https://travis-ci.org/macarthur-lab/seqr)

seqr is a web-based analysis tool for rare disease genomics.

This repository contains code that underlies the [Broad seqr instance](http://seqr.broadinstitute.org) and other seqr deployments.

## Technical Overview

seqr consists of the following components:
- seqr - the main client-server application. It consists of javascript + react.js on the client-side, python + django on the server-side.
- postgres - SQL database used by seqr and phenotips to store project metadata and user-generated content such as variant notes, etc.
- phenotips - 3rd-party web-based form for entering structured phenotype data.
- matchbox - a tool for connecting with the Match Maker Exchange.
- nginx - http server used as the main gateway between seqr and the internet.
- pipeline-runner - container for running hail pipelines to annotate and load new datasets.
- redis - in-memory cache used to speed up request handling.
- elasticsearch - NoSQL database used to store variant callsets.
- kibana - dashboard and visual interface for elasticsearch.
- mongo - legacy NoSQL database originally used for variant callsets and still used now to store some reference data and logs.

These components can be deployed on local or cloud-based hardware.
A laptop with 4 CPUs and 16G RAM may be sufficient for small datasets.
The seqr [production instance](http://seqr.broadinstitute.org) currently uses two n1-highmem-4 (4 vCPUs, 26 GB memory) servers on google cloud + separate servers for the elasticsearch database.
The pipeline for loading new datasets uses Spark to parallelize VEP and other annotation steps. This pipeline can run on the same machine that's hosting seqr components, but running on a separate Spark cluster will allow much processing and loading speeds proportional to the number of nodes and CPUs .


## Install

seqr can be installed on a laptop or on-prem server(s) using installation scripts in the deploy/ directory:
  
**[Detailed instructions for local installations](deploy/LOCAL_INSTALL.md)**.  

For cloud-based deployments, there are Docker images and Kubernetes configs: 

**[Detailed instructions for Kubernetes deployments](deploy/MINIKUBE.md)**.  



#### Prerequisites
 - *Hardware:*  At least **16 Gb RAM**, **2 CPUs**, **50 Gb disk space**  

 - *Software:*  
     - python2.7    
     - on MacOS only: [homebrew](http://brew.sh/) package manager  
     - on Linux only: root access with sudo
    

## Updating / Migrating an older xBrowse Instance

[Update/Migration Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/MIGRATE.md)


## Deploying and managing seqr components


The `./servctl` wrapper script provides sub-commands for deploying and interacting with seqr components running on kubernetes.

Run `./servctl -h` to see all available subcommands. The most commonly used ones are:

```
  ./servctl

      deploy-all  {deployment-target}                       # end-to-end deployment - deploys all seqr components and loads reference data
      deploy {component-name} {deployment-target}           # deploy some specific component(s)
          --restore-seqr-db-from-backup  <seqr_db_backup_file.sql.gz>   # deploying seqr with this option will also load the given seqrdb backup into postgres
          --restore-phenotips-db-from-backup  <xwiki_db_backup_file.sql.gz>   # deploying seqr with this option will also load the given phenotips xwikidb backup into postgres
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

      create-user {deployment-target}                       # create seqr superuser
      update-reference-data {deployment-target}             # update gene-level reference data in seqr
      load-example-project {deployment-target}              # run commands in seqr and pipeline-runner to load an example project


  *** {deployment-target} is one of:  minikube, gcloud-dev, or gcloud-prod
  *** {component-name} is one of: init-cluster, settings, secrets, nginx, postgres, phenotips, seqr,
                                  redis, pipeline-runner, matchbox, cockpit, kibana,
                                  external-mongo-connector, external-elasticsearch-connector,
                                  mongo, elasticsearch,
                                  es-client, es-master, es-data, es-kibana
```


## Data loading pipelines

seqr uses [hail](http://hail.is)-based pipelines to run VEP and add in other reference data before loading them into elasticsearch.
These pipelines can be run locally on a single machine or on-prem spark cluster, or on a cloud-based spark cluster like Google Dataproc.
We are working on integrating these pipelines so that they are launched and managed by seqr.
For now, they must be run manually, as shown in the examples below. The code for these pipelines is in [Data annotation and loading pipelines](https://github.com/macarthur-lab/hail-elasticsearch-pipelines)
and is automatically installed in the `pipeline-runner` component which is deployed as part of standard seqr deployment.

Example with seqr deployed to google cloud GKE, and using Google Dataproc to run the pipeline:
```
# these commands should be run locally on your laptop
git clone git@github.com:macarthur-lab/hail-elasticsearch-pipelines.git

cd hail-elasticsearch-pipelines
export IP=56.4.0.3   # IP address of elasticsearch instance running on google cloud on the project-default network so that it's visible to dataproc nodes, but not to the public internet.
export SEQR_PROJECT_GUID=R003_seqr_project3  # guid of existing seqr project
export GS_VCF_PATH=gs://seqr-datasets/GRCh38/my-new-dataset.vcf.gz   # VCF path on cloud storage

# this will create a new dataproc cluster and submit the pipeline to it
python gcloud_dataproc/load_dataset.py --genome-version GRCh38 --host $IP --project-guid SEQR_PROJECT_GUID --sample-type WGS --dataset-type VARIANTS $GS_VCF_PATH --es-block-size 50

# after the pipeline completes successfully, you can link the new elasticsearch index to the seqr project by using the 'Edit Datasets' dialog on the project page.
```


## Kubernetes Resources


- Official Kuberentes User Guide:  https://kubernetes.io/docs/user-guide/
- 15 Kubernetes Features in 15 Minutes: https://www.youtube.com/watch?v=o85VR90RGNQ
- Kubernetes: Up and Running: https://www.safaribooksonline.com/library/view/kubernetes-up-and/9781491935668/
- The Children's Illustrated Guide to Kubernetes: https://deis.com/blog/2016/kubernetes-illustrated-guide/
